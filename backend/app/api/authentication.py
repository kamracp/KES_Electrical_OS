"""
Authentication dependencies for the API (EOS-01 a).

require_user turns the session cookie into the signed-in identity or answers 401; require_role
adds the role check and answers 403. Both use the request's own database session, so the route
and its authentication share one unit of work.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.api.dependencies import DatabaseSession
from app.core.config import settings
from app.models.identity import OrganizationRole
from app.repositories.identity import IdentityRepository
from app.services.auth import (
    AuthenticatedSession,
    AuthService,
    RequestContext,
    SessionInvalidError,
)


def get_auth_service(db: DatabaseSession) -> AuthService:
    return AuthService(IdentityRepository(db))


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]


def get_request_context(request: Request) -> RequestContext:
    """
    Client address and browser for the audit trail. The address comes from the proxy headers
    (Cloudflare, then nginx); it is recorded, never used for an access decision.
    """

    forwarded_for = request.headers.get("x-forwarded-for", "")
    ip_address = (
        request.headers.get("cf-connecting-ip")
        or forwarded_for.split(",")[0].strip()
        or (request.client.host if request.client else None)
    )
    return RequestContext(
        ip_address=ip_address or None,
        user_agent=request.headers.get("user-agent"),
    )


RequestContextDependency = Annotated[RequestContext, Depends(get_request_context)]


def get_session_token(request: Request) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


async def require_user(
    request: Request,
    service: AuthServiceDependency,
) -> AuthenticatedSession:
    """The signed-in identity of this request; 401 when there is no valid session."""

    try:
        return await service.authenticate(get_session_token(request))
    except SessionInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


CurrentSession = Annotated[AuthenticatedSession, Depends(require_user)]


async def require_password_changed(identity: CurrentSession) -> AuthenticatedSession:
    """A first or reset password opens nothing but the password change itself."""

    if identity.user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Change your password before you continue.",
        )
    return identity


_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _forbidden(allowed_values: set[str]) -> HTTPException:
    needed = " or ".join(sorted(allowed_values))
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"This action needs the role {needed}.",
    )


def require_role(
    *allowed: OrganizationRole,
) -> Callable[[AuthenticatedSession], Awaitable[AuthenticatedSession]]:
    """A dependency that lets only the given roles pass; everybody else gets 403."""

    allowed_values = {role.value for role in allowed}

    async def dependency(identity: CurrentSession) -> AuthenticatedSession:
        if identity.role not in allowed_values:
            raise _forbidden(allowed_values)
        return identity

    return dependency


def require_role_for_writes(
    *allowed: OrganizationRole,
) -> Callable[[Request, AuthenticatedSession], Awaitable[AuthenticatedSession]]:
    """Reading (GET) is open to every signed-in member; any other method needs a given role."""

    allowed_values = {role.value for role in allowed}

    async def dependency(request: Request, identity: CurrentSession) -> AuthenticatedSession:
        if request.method not in _SAFE_METHODS and identity.role not in allowed_values:
            raise _forbidden(allowed_values)
        return identity

    return dependency


require_owner = require_role(OrganizationRole.OWNER)
require_engineer = require_role(OrganizationRole.OWNER, OrganizationRole.ENGINEER)

engineer_writes = require_role_for_writes(OrganizationRole.OWNER, OrganizationRole.ENGINEER)
owner_writes = require_role_for_writes(OrganizationRole.OWNER)

OwnerSession = Annotated[AuthenticatedSession, Depends(require_owner)]
EngineerSession = Annotated[AuthenticatedSession, Depends(require_engineer)]


__all__ = [
    "AuthServiceDependency",
    "CurrentSession",
    "EngineerSession",
    "OwnerSession",
    "RequestContextDependency",
    "engineer_writes",
    "get_auth_service",
    "get_request_context",
    "get_session_token",
    "owner_writes",
    "require_engineer",
    "require_owner",
    "require_password_changed",
    "require_role",
    "require_role_for_writes",
    "require_user",
]
