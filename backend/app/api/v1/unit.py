"""
Engineering Units API.
KESE-S1-M4
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import DatabaseSession
from app.repositories.unit import UnitRepository
from app.schemas.unit import UnitCreate, UnitResponse, UnitUpdate
from app.services.unit import UnitService

router = APIRouter(
    prefix="/units",
    tags=["Engineering Units"],
)


def get_service(
    db: DatabaseSession,
) -> UnitService:
    """Create an Engineering Units service for the request."""

    return UnitService(UnitRepository(db))


@router.post(
    "/",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_unit(
    payload: UnitCreate,
    db: DatabaseSession,
) -> UnitResponse:
    """Create a new Engineering Unit."""

    return await get_service(db).create(payload)


@router.get(
    "/",
    response_model=list[UnitResponse],
)
async def list_units(
    db: DatabaseSession,
) -> list[UnitResponse]:
    """Return all Engineering Units."""

    return await get_service(db).list()


@router.get(
    "/{unit_id}",
    response_model=UnitResponse,
)
async def get_unit(
    unit_id: UUID,
    db: DatabaseSession,
) -> UnitResponse:
    """Return an Engineering Unit by UUID."""

    unit = await get_service(db).get_by_id(unit_id)

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    return unit


@router.patch(
    "/{unit_id}",
    response_model=UnitResponse,
)
async def update_unit(
    unit_id: UUID,
    payload: UnitUpdate,
    db: DatabaseSession,
) -> UnitResponse:
    """Partially update an Engineering Unit."""

    service = get_service(db)
    unit = await service.get_by_id(unit_id)

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    return await service.update(
        unit,
        payload,
    )


@router.delete(
    "/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_unit(
    unit_id: UUID,
    db: DatabaseSession,
) -> None:
    """Delete an Engineering Unit."""

    service = get_service(db)
    unit = await service.get_by_id(unit_id)

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    await service.delete(unit)