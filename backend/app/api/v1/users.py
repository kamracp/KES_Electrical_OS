"""
User administration for organization owners (EOS-01 a).

The whole router is included with the owner requirement (see app.api.router), reading
included: the user list and the sign-in audit trail are not for every member.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.authentication import OwnerSession, RequestContextDependency
from app.api.dependencies import DatabaseSession
from app.core.security import PasswordPolicyError
from app.repositories.identity import IdentityRepository
from app.schemas.identity import (
    AuthEventListResponse,
    AuthEventResponse,
    PasswordResetRequest,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services.user_admin import (
    UserAdminService,
    UserConflictError,
    UserNotFoundError,
    UserRecord,
)

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_admin_service(db: DatabaseSession) -> UserAdminService:
    return UserAdminService(IdentityRepository(db))


UserAdminDependency = Annotated[UserAdminService, Depends(get_user_admin_service)]


def _user_response(record: UserRecord) -> UserResponse:
    user = record.user
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=record.membership.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        locked_until=user.locked_until,
        last_login_at=user.last_login_at,
    )


def _not_found(exc: UserNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _conflict(exc: UserConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _policy(exc: PasswordPolicyError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("", response_model=UserListResponse)
async def list_users(actor: OwnerSession, service: UserAdminDependency) -> UserListResponse:
    """All users of the owner's organization, active or not."""

    items = [_user_response(record) for record in await service.list_users(actor)]
    return UserListResponse(items=items, total=len(items))


@router.get("/events", response_model=AuthEventListResponse)
async def list_auth_events(
    actor: OwnerSession,
    service: UserAdminDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AuthEventListResponse:
    """The sign-in and user-administration audit trail, newest first."""

    events = await service.list_events(limit=limit)
    return AuthEventListResponse(
        items=[AuthEventResponse.model_validate(event) for event in events]
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    actor: OwnerSession,
    service: UserAdminDependency,
    context: RequestContextDependency,
) -> UserResponse:
    """Create a user with a first password; by default it must be changed at first sign-in."""

    try:
        record = await service.create_user(
            actor,
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            password=payload.password.get_secret_value(),
            must_change_password=payload.must_change_password,
            context=context,
        )
    except UserConflictError as exc:
        raise _conflict(exc) from exc
    except PasswordPolicyError as exc:
        raise _policy(exc) from exc
    return _user_response(record)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    actor: OwnerSession,
    service: UserAdminDependency,
    context: RequestContextDependency,
) -> UserResponse:
    """Rename, change the role, deactivate or reactivate; deactivating closes the sessions."""

    try:
        record = await service.update_user(
            actor,
            user_id,
            full_name=payload.full_name,
            role=payload.role,
            is_active=payload.is_active,
            context=context,
        )
    except UserNotFoundError as exc:
        raise _not_found(exc) from exc
    except UserConflictError as exc:
        raise _conflict(exc) from exc
    return _user_response(record)


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    user_id: UUID,
    payload: PasswordResetRequest,
    actor: OwnerSession,
    service: UserAdminDependency,
    context: RequestContextDependency,
) -> None:
    """Set a new first password; the user's sessions are closed and a change is required."""

    try:
        await service.reset_password(
            actor, user_id, payload.new_password.get_secret_value(), context
        )
    except UserNotFoundError as exc:
        raise _not_found(exc) from exc
    except UserConflictError as exc:
        raise _conflict(exc) from exc
    except PasswordPolicyError as exc:
        raise _policy(exc) from exc
