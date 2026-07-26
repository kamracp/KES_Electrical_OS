"""
Repository for Engineering Units.
KESE-S1-M2
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unit import Unit


class UnitRepository:
    """Repository for Unit database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, unit: Unit) -> Unit:
        self.db.add(unit)
        await self.db.commit()
        await self.db.refresh(unit)
        return unit

    async def get_by_id(self, unit_id: UUID) -> Unit | None:
        return await self.db.get(Unit, unit_id)

    async def get_by_code(self, code: str) -> Unit | None:
        stmt = select(Unit).where(Unit.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self) -> list[Unit]:
        stmt = select(Unit).order_by(Unit.quantity, Unit.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, unit: Unit) -> Unit:
        await self.db.commit()
        await self.db.refresh(unit)
        return unit

    async def delete(self, unit: Unit) -> None:
        await self.db.delete(unit)
        await self.db.commit()