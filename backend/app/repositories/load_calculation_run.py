"""
Repository for persistent electrical load calculation runs.
KESE-S2-M3
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.load_calculation_run import (
    CalculationApprovalStatus,
    LoadCalculationRun,
)


class LoadCalculationRunRepository:
    """
    Repository for load calculation run persistence and retrieval.

    Calculation runs are retained as audit records. This repository
    intentionally provides no delete operation.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def create(
        self,
        calculation_run: LoadCalculationRun,
    ) -> LoadCalculationRun:
        """Persist and return a new calculation run."""

        self.db.add(calculation_run)
        await self.db.commit()
        await self.db.refresh(calculation_run)

        return calculation_run

    async def get_by_id(
        self,
        run_id: UUID,
    ) -> LoadCalculationRun | None:
        """Return a calculation run by UUID."""

        return await self.db.get(
            LoadCalculationRun,
            run_id,
        )

    async def get_latest_revision(
        self,
        calculation_key: str,
    ) -> LoadCalculationRun | None:
        """Return the latest revision for a calculation key."""

        stmt = (
            select(LoadCalculationRun)
            .where(
                LoadCalculationRun.calculation_key
                == calculation_key
            )
            .order_by(
                LoadCalculationRun.revision_number.desc(),
            )
            .limit(1)
        )

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def get_next_revision_number(
        self,
        calculation_key: str,
    ) -> int:
        """Return the next available revision number."""

        stmt = select(
            func.coalesce(
                func.max(
                    LoadCalculationRun.revision_number
                ),
                0,
            )
            + 1
        ).where(
            LoadCalculationRun.calculation_key
            == calculation_key
        )

        result = await self.db.execute(stmt)

        return int(result.scalar_one())

    async def get_latest_by_content_hash(
        self,
        content_hash: str,
    ) -> LoadCalculationRun | None:
        """Return the latest run having the supplied content hash."""

        stmt = (
            select(LoadCalculationRun)
            .where(
                LoadCalculationRun.content_hash
                == content_hash
            )
            .order_by(
                LoadCalculationRun.created_at.desc(),
            )
            .limit(1)
        )

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def list_by_calculation_key(
        self,
        calculation_key: str,
    ) -> list[LoadCalculationRun]:
        """Return complete revision history, newest first."""

        stmt = (
            select(LoadCalculationRun)
            .where(
                LoadCalculationRun.calculation_key
                == calculation_key
            )
            .order_by(
                LoadCalculationRun.revision_number.desc(),
            )
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def list_pending_review(
        self,
    ) -> list[LoadCalculationRun]:
        """Return calculation runs waiting for engineering review."""

        stmt = (
            select(LoadCalculationRun)
            .where(
                LoadCalculationRun.approval_status
                == CalculationApprovalStatus.PENDING.value
            )
            .order_by(
                LoadCalculationRun.submitted_at.asc().nulls_last(),
                LoadCalculationRun.created_at.asc(),
            )
        )

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def save(
        self,
        calculation_run: LoadCalculationRun,
    ) -> LoadCalculationRun:
        """
        Commit a controlled calculation-run state transition.

        Approval and immutability rules will be enforced by the service
        layer before this method is called.
        """

        await self.db.commit()
        await self.db.refresh(calculation_run)

        return calculation_run


__all__ = [
    "LoadCalculationRunRepository",
]