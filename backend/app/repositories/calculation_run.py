"""
Repository for the generic engineering calculation-run audit table.

Runs are retained as evidence records: there is intentionally no delete.
Every lookup is scoped by module code so calculation keys may repeat across
modules (a cable study and a fault study may share a project code).
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calculation_run import CalculationRun


class CalculationRunRepository:
    """Persistence and retrieval for CalculationRun records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, calculation_run: CalculationRun) -> CalculationRun:
        """Persist and return a new calculation run."""

        self.db.add(calculation_run)
        await self.db.commit()
        await self.db.refresh(calculation_run)
        return calculation_run

    async def get_by_id(self, run_id: UUID) -> CalculationRun | None:
        """Return a calculation run by UUID."""

        return await self.db.get(CalculationRun, run_id)

    async def get_latest_revision(
        self,
        module_code: str,
        calculation_key: str,
    ) -> CalculationRun | None:
        """Return the highest revision for a module and calculation key."""

        stmt = (
            select(CalculationRun)
            .where(
                CalculationRun.module_code == module_code,
                CalculationRun.calculation_key == calculation_key,
            )
            .order_by(CalculationRun.revision_number.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_revision_number(
        self,
        module_code: str,
        calculation_key: str,
    ) -> int:
        """Return the next available revision number for a module and key."""

        stmt = select(func.coalesce(func.max(CalculationRun.revision_number), 0) + 1).where(
            CalculationRun.module_code == module_code,
            CalculationRun.calculation_key == calculation_key,
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def list_by_calculation_key(
        self,
        module_code: str,
        calculation_key: str,
    ) -> list[CalculationRun]:
        """Return every revision for a module and key, newest first."""

        stmt = (
            select(CalculationRun)
            .where(
                CalculationRun.module_code == module_code,
                CalculationRun.calculation_key == calculation_key,
            )
            .order_by(CalculationRun.revision_number.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(self, module_code: str, limit: int = 20) -> list[CalculationRun]:
        """Return the most recent runs of a module, newest first."""

        stmt = (
            select(CalculationRun)
            .where(CalculationRun.module_code == module_code)
            .order_by(CalculationRun.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def save(self, calculation_run: CalculationRun) -> CalculationRun:
        """Commit a controlled state transition validated by the service layer."""

        await self.db.commit()
        await self.db.refresh(calculation_run)
        return calculation_run


__all__ = ["CalculationRunRepository"]
