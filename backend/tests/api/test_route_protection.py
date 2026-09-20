"""
Every API route needs a signed-in user unless it is on the short public list below (EOS-01 a).

The test walks the application's own published route table (its OpenAPI description), so a
router added later without protection fails here instead of going live open.
"""

import re
from collections.abc import Callable
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from httpx import AsyncClient

from app.api.router import REFERENCE_DATA_ROUTERS, STUDY_ROUTERS
from app.core.config import settings
from app.main import app
from app.models.identity import OrganizationRole

pytestmark = pytest.mark.api

API = settings.API_V1_PREFIX
PUBLIC_ROUTES = {
    ("GET", f"{API}/health"),
    ("GET", f"{API}/version"),
    ("POST", f"{API}/auth/login"),
    ("POST", f"{API}/auth/logout"),
}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def api_routes() -> list[tuple[str, str]]:
    """Every (method, path) the application publishes, read from its OpenAPI description."""

    paths = app.openapi()["paths"]
    return sorted(
        (method.upper(), path)
        for path, operations in paths.items()
        if path.startswith(API)
        for method in operations
        if method.upper() in HTTP_METHODS
    )


def concrete(path: str) -> str:
    """Fill path parameters such as {run_id} with a value."""

    return re.sub(r"\{[^}]+\}", str(uuid4()), path)


def router_paths(routers: tuple, *, writes: bool) -> list[tuple[str, str]]:
    found = []
    for router in routers:
        for route in router.routes:
            if isinstance(route, APIRoute):
                for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                    if (method not in SAFE_METHODS) == writes:
                        found.append((method, concrete(f"{API}{route.path}")))
    return found


def test_the_public_list_names_real_routes() -> None:
    routes = set(api_routes())

    assert routes >= PUBLIC_ROUTES, "a public route was renamed: update PUBLIC_ROUTES on purpose"


async def test_every_route_outside_the_public_list_answers_401_without_a_session(
    anonymous_client: AsyncClient,
) -> None:
    protected = [route for route in api_routes() if route not in PUBLIC_ROUTES]
    assert len(protected) >= 12, "the route table looks empty: the walk would prove nothing"

    open_routes = []
    for method, path in protected:
        response = await anonymous_client.request(method, concrete(path), json={})
        if response.status_code != 401:
            open_routes.append(f"{method} {path} -> {response.status_code}")

    assert open_routes == []


async def test_health_and_version_stay_open_for_the_deploy_checks(
    anonymous_client: AsyncClient,
) -> None:
    assert (await anonymous_client.get(f"{API}/health")).status_code == 200
    assert (await anonymous_client.get(f"{API}/version")).status_code == 200


async def test_a_viewer_may_read_but_not_calculate_or_save(
    sign_in_as: Callable[[OrganizationRole], AsyncClient],
) -> None:
    viewer = sign_in_as(OrganizationRole.VIEWER)
    writes = router_paths(STUDY_ROUTERS, writes=True)
    reads = router_paths(STUDY_ROUTERS + REFERENCE_DATA_ROUTERS, writes=False)
    assert writes and reads

    for method, path in writes:
        response = await viewer.request(method, path, json={})
        assert response.status_code == 403, f"{method} {path} -> {response.status_code}"
        assert response.json()["detail"] == "This action needs the role ENGINEER or OWNER."
    for method, path in reads:
        response = await viewer.request(method, path)
        assert response.status_code not in {401, 403}, f"{method} {path}"


async def test_an_engineer_may_calculate_but_not_change_reference_data(
    sign_in_as: Callable[[OrganizationRole], AsyncClient],
) -> None:
    engineer = sign_in_as(OrganizationRole.ENGINEER)
    reference_writes = router_paths(REFERENCE_DATA_ROUTERS, writes=True)
    assert reference_writes

    for method, path in reference_writes:
        response = await engineer.request(method, path, json={})
        assert response.status_code == 403, f"{method} {path} -> {response.status_code}"
        assert response.json()["detail"] == "This action needs the role OWNER."
    for method, path in router_paths(STUDY_ROUTERS, writes=True):
        response = await engineer.request(method, path, json={})
        assert response.status_code not in {401, 403}, f"{method} {path}"


async def test_an_owner_passes_every_role_check(client: AsyncClient) -> None:
    for method, path in router_paths(STUDY_ROUTERS + REFERENCE_DATA_ROUTERS, writes=True):
        response = await client.request(method, path, json={})
        assert response.status_code not in {401, 403}, f"{method} {path}"
