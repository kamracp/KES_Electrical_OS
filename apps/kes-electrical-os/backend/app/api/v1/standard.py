"""
Engineering Standards API.
KESE-S1-M3
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import DatabaseSession
from app.repositories.standard import StandardRepository
from app.schemas.standard import (
    StandardCreate,
    StandardResponse,
    StandardUpdate,
)
from app.services.standard import StandardService

router = APIRouter(
    prefix="/standards",
    tags=["Engineering Standards"],
)


def get_service(
    db: DatabaseSession,
) -> StandardService:
    """Create an Engineering Standards service for the request."""

    return StandardService(StandardRepository(db))


@router.post(
    "/",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_standard(
    payload: StandardCreate,
    db: DatabaseSession,
) -> StandardResponse:
    """Create a new Engineering Standard."""

    service = get_service(db)

    existing_standard = await service.get_by_code(payload.code)

    if existing_standard is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Standard code already exists",
        )

    return await service.create(payload)


@router.get(
    "/",
    response_model=list[StandardResponse],
)
async def list_standards(
    db: DatabaseSession,
) -> list[StandardResponse]:
    """Return all Engineering Standards."""

    return await get_service(db).list()


@router.get(
    "/{standard_id}",
    response_model=StandardResponse,
)
async def get_standard(
    standard_id: UUID,
    db: DatabaseSession,
) -> StandardResponse:
    """Return an Engineering Standard by UUID."""

    standard = await get_service(db).get_by_id(
        standard_id
    )

    if standard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Standard not found",
        )

    return standard


@router.patch(
    "/{standard_id}",
    response_model=StandardResponse,
)
async def update_standard(
    standard_id: UUID,
    payload: StandardUpdate,
    db: DatabaseSession,
) -> StandardResponse:
    """Partially update an Engineering Standard."""

    service = get_service(db)

    standard = await service.get_by_id(standard_id)

    if standard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Standard not found",
        )

    if (
        payload.code is not None
        and payload.code != standard.code
    ):
        standard_with_code = await service.get_by_code(
            payload.code
        )

        if standard_with_code is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Standard code already exists",
            )

    return await service.update(
        standard,
        payload,
    )


@router.delete(
    "/{standard_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_standard(
    standard_id: UUID,
    db: DatabaseSession,
) -> None:
    """Delete an Engineering Standard."""

    service = get_service(db)

    standard = await service.get_by_id(standard_id)

    if standard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Standard not found",
        )

    await service.delete(standard)