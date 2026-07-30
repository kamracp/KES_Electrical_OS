"""
Persistent audit model for electrical load and demand calculation runs.
KESE-S2-M3
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class CalculationRunType(StrEnum):
    """Supported persistent calculation-run types."""

    SINGLE_LOAD = "SINGLE_LOAD"
    LOAD_GROUP = "LOAD_GROUP"


class CalculationRunStatus(StrEnum):
    """Execution status of a calculation run."""

    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CalculationApprovalStatus(StrEnum):
    """Engineering review and approval status."""

    NOT_SUBMITTED = "NOT_SUBMITTED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LoadCalculationRun(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """
    Immutable audit record for an electrical calculation run.

    Every run stores complete input, result, assumption, warning and
    standards snapshots. A changed calculation must be stored as a new
    revision instead of overwriting an approved run.
    """

    __tablename__ = "load_calculation_runs"

    __table_args__ = (
        UniqueConstraint(
            "calculation_key",
            "revision_number",
            name="calculation_key_revision_unique",
        ),
        CheckConstraint(
            "revision_number > 0",
            name="revision_number_positive",
        ),
        CheckConstraint(
            (
                "calculation_type IN "
                "('SINGLE_LOAD', 'LOAD_GROUP')"
            ),
            name="calculation_type_valid",
        ),
        CheckConstraint(
            (
                "scenario IN "
                "('NORMAL', 'EMERGENCY', 'OUTAGE', "
                "'STARTING', 'UPS', 'PV', 'FUTURE')"
            ),
            name="scenario_valid",
        ),
        CheckConstraint(
            (
                "run_status IN "
                "('DRAFT', 'COMPLETED', 'FAILED')"
            ),
            name="run_status_valid",
        ),
        CheckConstraint(
            (
                "approval_status IN "
                "('NOT_SUBMITTED', 'PENDING', "
                "'APPROVED', 'REJECTED')"
            ),
            name="approval_status_valid",
        ),
        CheckConstraint(
            (
                "approval_status <> 'APPROVED' OR "
                "("
                "approved_by IS NOT NULL AND "
                "approved_at IS NOT NULL AND "
                "is_immutable = true"
                ")"
            ),
            name="approved_run_audit_complete",
        ),
        CheckConstraint(
            (
                "approval_status <> 'REJECTED' OR "
                "("
                "rejected_by IS NOT NULL AND "
                "rejected_at IS NOT NULL AND "
                "rejection_reason IS NOT NULL"
                ")"
            ),
            name="rejected_run_audit_complete",
        ),
        CheckConstraint(
            (
                "is_immutable = false OR "
                "approval_status = 'APPROVED'"
            ),
            name="immutable_only_when_approved",
        ),
        CheckConstraint(
            (
                "supersedes_run_id IS NULL OR "
                "supersedes_run_id <> id"
            ),
            name="run_cannot_supersede_itself",
        ),
        Index(
            "ix_load_calculation_runs_revision_lookup",
            "calculation_key",
            "scenario",
            "revision_number",
        ),
        Index(
            "ix_load_calculation_runs_review_queue",
            "approval_status",
            "created_at",
        ),
    )

    calculation_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    revision_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    calculation_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    scenario: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    run_status: Mapped[str] = mapped_column(
        String(30),
        default=CalculationRunStatus.COMPLETED.value,
        nullable=False,
        index=True,
    )

    approval_status: Mapped[str] = mapped_column(
        String(30),
        default=CalculationApprovalStatus.NOT_SUBMITTED.value,
        nullable=False,
        index=True,
    )

    engine_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    formula_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    input_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    result_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    assumptions_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    warnings_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    standards_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
    )

    calculated_by: Mapped[str | None] = mapped_column(
        String(200),
    )

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    submitted_by: Mapped[str | None] = mapped_column(
        String(200),
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    approved_by: Mapped[str | None] = mapped_column(
        String(200),
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    approval_notes: Mapped[str | None] = mapped_column(
        Text,
    )

    rejected_by: Mapped[str | None] = mapped_column(
        String(200),
    )

    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
    )

    supersedes_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "load_calculation_runs.id",
            ondelete="RESTRICT",
        ),
        index=True,
    )

    is_immutable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
    )

    def __repr__(self) -> str:
        return (
            "<LoadCalculationRun("
            f"calculation_key='{self.calculation_key}', "
            f"revision_number={self.revision_number}, "
            f"scenario='{self.scenario}', "
            f"approval_status='{self.approval_status}'"
            ")>"
        )


__all__ = [
    "CalculationApprovalStatus",
    "CalculationRunStatus",
    "CalculationRunType",
    "LoadCalculationRun",
]