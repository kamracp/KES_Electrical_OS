"""
Repository for Standards Registry.
KEOS-S1-M1
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.standard import Standard


class StandardRepository:
    """Repository for Standard database operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, standard: Standard) -> Standard:
        """Create a new standard."""
        self._session.add(standard)
        await self._session.commit()
        await self._session.refresh(standard)
        return standard

    async def get(self, standard_id: UUID) -> Standard | None:
        """Get a standard by UUID."""
        result = await self._session.execute(
            select(Standard).where(Standard.id == standard_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Standard | None:
        """Get a standard by code."""
        result = await self._session.execute(
            select(Standard).where(Standard.code == code)
        )
        return result.scalar_one_or_none()

    async def list(self) -> list[Standard]:
        """List all standards."""
        result = await self._session.execute(
            select(Standard).order_by(Standard.code)
        )
        return list(result.scalars().all())

    async def update(self, standard: Standard) -> Standard:
        """Persist changes to a standard."""
        await self._session.commit()
        await self._session.refresh(standard)
        return standard

    async def delete(self, standard: Standard) -> None:
        """Delete a standard."""
        await self._session.delete(standard)
        await self._session.commit()