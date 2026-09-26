"""The name on a run or a review action is the signed-in user, never request data (EOS-01 a)."""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from app.models.identity import OrganizationRole
from app.services.auth import AuthenticatedSession

pytestmark = pytest.mark.api

API = "/api/v1/electrical"
CASES = [
    (f"{API}/cable/runs", "calculated_by"),
    (f"{API}/fault/runs", "calculated_by"),
    (f"{API}/load-demand/runs", "calculated_by"),
    (f"{API}/transformer-sizing/runs", "calculated_by"),
]


@pytest.mark.parametrize(("url", "field"), CASES)
async def test_a_request_cannot_carry_the_name_of_a_person(
    client: AsyncClient, url: str, field: str
) -> None:
    response = await client.post(url, json={field: "Somebody Else"})

    assert response.status_code == 422
    refused = [error for error in response.json()["detail"] if error["loc"] == ["body", field]]
    assert [error["type"] for error in refused] == ["extra_forbidden"]


def test_the_label_names_the_person_and_the_email(
    make_identity: Callable[[OrganizationRole], AuthenticatedSession],
) -> None:
    identity = make_identity(OrganizationRole.ENGINEER)

    assert identity.label == "Test Engineer (engineer@example.com)"


def test_the_label_fits_the_column_of_the_record(
    make_identity: Callable[[OrganizationRole], AuthenticatedSession],
) -> None:
    identity = make_identity(OrganizationRole.OWNER)
    identity.user.full_name = "N" * 250

    assert len(identity.label) == 200
