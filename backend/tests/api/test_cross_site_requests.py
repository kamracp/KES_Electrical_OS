"""
Cross-site request forgery: the requests a foreign page can send without asking first.

The session cookie is SameSite=Strict, so another site never gets it attached. The sibling
products on other sub-domains of the same registrable domain are "same-site" to a browser,
though, and a page there can send a so-called simple request (a form post, or a fetch with
Content-Type text/plain) together with the cookie, without a CORS preflight. A request with
Content-Type application/json always needs the preflight, and this API answers no preflight
because it installs no CORS middleware.

So the remaining door is a simple request whose body merely looks like JSON. These tests pin
that the API does not read such a body as JSON: a state-changing route answers 422 and does
nothing. If a framework upgrade ever changes that, this file fails.
"""

import json

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

PASSWORD_CHANGE = "/api/v1/auth/password"
BODY = json.dumps(
    {"current_password": "not the current one", "new_password": "a brand new passphrase"}
)

SIMPLE_CONTENT_TYPES = (
    "text/plain",
    "text/plain;charset=UTF-8",
    "application/x-www-form-urlencoded",
    "multipart/form-data; boundary=x",
)


@pytest.mark.parametrize("content_type", SIMPLE_CONTENT_TYPES)
async def test_a_simple_request_is_not_read_as_json(client: AsyncClient, content_type: str) -> None:
    response = await client.post(
        PASSWORD_CHANGE,
        content=BODY,
        headers={"content-type": content_type},
    )

    assert response.status_code == 422, response.text


async def test_a_body_without_any_content_type_is_not_read_as_json(client: AsyncClient) -> None:
    """A page can post a Blob without a type: no Content-Type header and no preflight."""

    response = await client.post(PASSWORD_CHANGE, content=BODY)

    assert "content-type" not in response.request.headers
    assert response.status_code == 422, response.text


async def test_the_same_body_as_json_reaches_the_service(client: AsyncClient) -> None:
    """The control case: with application/json the route runs and refuses the wrong password."""

    response = await client.post(
        PASSWORD_CHANGE,
        content=BODY,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400, response.text


async def test_no_preflight_is_answered(anonymous_client: AsyncClient) -> None:
    """Without CORS middleware a preflight gets no Access-Control-Allow-* header at all."""

    response = await anonymous_client.options(
        PASSWORD_CHANGE,
        headers={
            "origin": "https://other.example.com",
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )

    allowed = [name for name in response.headers if name.lower().startswith("access-control-")]
    assert allowed == []
