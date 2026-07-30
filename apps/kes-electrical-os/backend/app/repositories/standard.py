"""
Repository for Engineering Standards.
KESE-S1-M3
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.standard import Standard


class StandardRepository:
    """Repository for Engineering Standard database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, standard: Standard) -> Standard:
        """Persist and return a new Engineering Standard."""

        self.db.add(standard)
        await self.db.commit()
        await self.db.refresh(standard)

        return standard

    async def get_by_id(
        self,
        standard_id: UUID,
    ) -> Standard | None:
        """Return an Engineering Standard by UUID."""

        return await self.db.get(Standard, standard_id)

    async def get_by_code(
        self,
        code: str,
    ) -> Standard | None:
        """Return an Engineering Standard by its unique code."""

        stmt = select(Standard).where(Standard.code == code)
        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def list(self) -> list[Standard]:
        """Return all Engineering Standards in a stable order."""

        stmt = select(Standard).order_by(
            Standard.issuing_organization,
            Standard.code,
        )
        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def update(
        self,
        standard: Standard,
    ) -> Standard:
        """Commit changes made to an Engineering Standard."""

        await self.db.commit()
        await self.db.refresh(standard)

        return standard

    async def delete(
        self,
        standard: Standard,
    ) -> None:
        """Delete an Engineering Standard."""

        await self.db.delete(standard)
        await self.db.commit()
