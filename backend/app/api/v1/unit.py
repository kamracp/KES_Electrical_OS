"""
Engineering Units API.
KESE-S1-M2
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.unit import UnitRepository
from app.schemas.unit import UnitCreate, UnitResponse, UnitUpdate
from app.services.unit import UnitService

router = APIRouter(
    prefix="/units",
    tags=["Engineering Units"],
)


def get_service(db: AsyncSession) -> UnitService:
    return UnitService(UnitRepository(db))


@router.post(
    "/",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_unit(
    payload: UnitCreate,
    db: AsyncSession = Depends(get_db_session),
):
    return await get_service(db).create(payload)


@router.get("/", response_model=list[UnitResponse])
async def list_units(
    db: AsyncSession = Depends(get_db_session),
):
    return await get_service(db).list()


@router.get("/{unit_id}", response_model=UnitResponse)
async def get_unit(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    unit = await get_service(db).get_by_id(unit_id)

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    return unit


@router.patch("/{unit_id}", response_model=UnitResponse)
async def update_unit(
    unit_id: UUID,
    payload: UnitUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    service = get_service(db)
    unit = await service.get_by_id(unit_id)

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    return await service.update(unit, payload)


@router.delete(
    "/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_unit(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    service = get_service(db)
    unit = await service.get_by_id(unit_id)

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    await service.delete(unit)