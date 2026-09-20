"""
Sign-in, sign-out, current session and password change (EOS-01 a).

The session token travels only in an HttpOnly cookie (Secure outside development,
SameSite=Strict): page scripts cannot read it, and another site cannot make the browser send
it. Nothing here returns the token in a response body.
"""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.authentication import (
    AuthServiceDependency,
    CurrentSession,
    RequestContextDependency,
    get_session_token,
)
from app.core.config import settings
from app.core.security import PasswordPolicyError
from app.schemas.identity import (
    CurrentUser,
    LoginRequest,
    OrganizationSummary,
    PasswordChangeRequest,
    SessionResponse,
)
from app.services.auth import (
    AuthenticatedSession,
    InvalidCredentialsError,
    PasswordChangeError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _session_response(identity: AuthenticatedSession) -> SessionResponse:
    return SessionResponse(
        user=CurrentUser.model_validate(identity.user),
        organization=OrganizationSummary.model_validate(identity.organization),
        role=identity.membership.role,
        session_expires_at=identity.session.expires_at,
        idle_timeout_minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES,
    )


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_ABSOLUTE_LIFETIME_HOURS * 3600,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="strict",
    )


@router.post("/login", response_model=SessionResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> SessionResponse:
    """Sign in with e-mail and password; the session cookie is set on success."""

    try:
        token, identity = await service.login(
            payload.email,
            payload.password.get_secret_value(),
            context,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    _set_session_cookie(response, token)
    response.headers["Cache-Control"] = "no-store"
    return _session_response(identity)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> None:
    """Close the session on the server and remove the cookie; safe to call twice."""

    await service.logout(get_session_token(request), context)
    _clear_session_cookie(response)


@router.get("/me", response_model=SessionResponse)
async def me(identity: CurrentSession, response: Response) -> SessionResponse:
    """Who is signed in; 401 when there is no valid session."""

    response.headers["Cache-Control"] = "no-store"
    return _session_response(identity)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChangeRequest,
    identity: CurrentSession,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> None:
    """Change the own password; the user's other sessions are closed."""

    try:
        await service.change_password(
            identity,
            payload.current_password.get_secret_value(),
            payload.new_password.get_secret_value(),
            context,
        )
    except PasswordChangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
