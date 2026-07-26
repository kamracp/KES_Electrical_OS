"""
Service layer for Engineering Units.
KESE-S1-M2
"""

from uuid import UUID

from app.models.unit import Unit
from app.repositories.unit import UnitRepository
from app.schemas.unit import UnitCreate, UnitUpdate


class UnitService:
    """Business logic for Engineering Units."""

    def __init__(self, repository: UnitRepository):
        self.repository = repository

    async def create(self, payload: UnitCreate) -> Unit:
        unit = Unit(**payload.model_dump())
        return await self.repository.create(unit)

    async def list(self) -> list[Unit]:
        return await self.repository.list()

    async def get_by_id(self, unit_id: UUID) -> Unit | None:
        return await self.repository.get_by_id(unit_id)

    async def update(
        self,
        unit: Unit,
        payload: UnitUpdate,
    ) -> Unit:
        updates = payload.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(unit, field, value)

        return await self.repository.update(unit)

    async def delete(self, unit: Unit) -> None:
        await self.repository.delete(unit)