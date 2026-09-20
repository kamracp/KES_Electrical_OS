"""
The session cookie as the browser receives it (security review, finding F1).

Sign-out is public and always answers with the instruction to remove the cookie, so it shows
the cookie's name and attributes without needing a user in the database.
"""

import pytest
from fastapi import Request
from httpx import AsyncClient

from app.api.authentication import get_session_token
from app.core.config import settings

pytestmark = pytest.mark.asyncio

LOGOUT = "/api/v1/auth/logout"


def _request_with_cookie(header: str) -> Request:
    return Request({"type": "http", "headers": [(b"cookie", header.encode("ascii"))]})


async def test_a_secure_cookie_has_the_host_prefix_and_names_no_domain(
    anonymous_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", True)

    response = await anonymous_client.post(LOGOUT)

    header = response.headers["set-cookie"]
    attributes = [part.strip().lower() for part in header.split(";")[1:]]
    assert header.startswith('__Host-keos_session=""')
    assert "secure" in attributes
    assert "httponly" in attributes
    assert "samesite=strict" in attributes
    assert "path=/" in attributes
    assert not any(attribute.startswith("domain") for attribute in attributes)


async def test_plain_http_development_keeps_the_plain_name(
    anonymous_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", False)

    response = await anonymous_client.post(LOGOUT)

    header = response.headers["set-cookie"]
    assert header.startswith('keos_session=""')
    assert "secure" not in [part.strip().lower() for part in header.split(";")[1:]]


async def test_the_session_is_read_only_from_the_prefixed_cookie_when_secure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", True)

    assert get_session_token(_request_with_cookie("__Host-keos_session=abc")) == "abc"
    # A cookie with the plain name could have been set by a sibling sub-domain: it is ignored.
    assert get_session_token(_request_with_cookie("keos_session=planted")) is None
