"""
Persistent audit model for engineering calculation runs of any module.

One table serves every EOS module: the module code and calculation type
identify the engine, and the snapshots freeze the evidence a report or a
review consumes (Master Prompt v2.1 sections 4.12, 19 and 20).
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

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.load_calculation_run import (
    CalculationApprovalStatus,
    CalculationRunStatus,
)


class EngineeringCalculationType(StrEnum):
    """Calculation engines that persist runs through this table."""

    CABLE_SIZING = "CABLE_SIZING"
    SHORT_CIRCUIT = "SHORT_CIRCUIT"


class CalculationRun(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """
    Immutable audit record for one engineering calculation run.

    A run is written once by the service that executed the engine. Changes
    to inputs create a new revision of the same calculation key; an approved
    run is immutable and may only be superseded.
    """

    __tablename__ = "calculation_runs"

    __table_args__ = (
        UniqueConstraint(
            "module_code",
            "calculation_key",
            "revision_number",
            name="calculation_runs_key_revision_unique",
        ),
        CheckConstraint(
            "revision_number > 0",
            name="calculation_runs_revision_positive",
        ),
        CheckConstraint(
            "module_code LIKE 'EOS-__'",
            name="calculation_runs_module_code_format",
        ),
        CheckConstraint(
            ("calculation_type IN ('CABLE_SIZING', 'SHORT_CIRCUIT')"),
            name="calculation_runs_type_valid",
        ),
        CheckConstraint(
            ("run_status IN ('DRAFT', 'COMPLETED', 'FAILED')"),
            name="calculation_runs_status_valid",
        ),
        CheckConstraint(
            ("approval_status IN ('NOT_SUBMITTED', 'PENDING', 'APPROVED', 'REJECTED')"),
            name="calculation_runs_approval_valid",
        ),
        CheckConstraint(
            (
                "approval_status <> 'APPROVED' OR "
                "(approved_by IS NOT NULL AND approved_at IS NOT NULL AND is_immutable = true)"
            ),
            name="calculation_runs_approved_audit_complete",
        ),
        CheckConstraint(
            (
                "approval_status <> 'REJECTED' OR "
                "(rejected_by IS NOT NULL AND rejected_at IS NOT NULL "
                "AND rejection_reason IS NOT NULL)"
            ),
            name="calculation_runs_rejected_audit_complete",
        ),
        CheckConstraint(
            ("is_immutable = false OR approval_status = 'APPROVED'"),
            name="calculation_runs_immutable_only_when_approved",
        ),
        CheckConstraint(
            ("supersedes_run_id IS NULL OR supersedes_run_id <> id"),
            name="calculation_runs_cannot_supersede_itself",
        ),
        Index(
            "ix_calculation_runs_revision_lookup",
            "module_code",
            "calculation_key",
            "revision_number",
        ),
        Index(
            "ix_calculation_runs_review_queue",
            "approval_status",
            "created_at",
        ),
    )

    module_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    calculation_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    calculation_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

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

    # Engine identity and the design-check outcome, frozen with the run.
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)
    design_check_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    jurisdiction_profile: Mapped[str] = mapped_column(String(10), nullable=False)
    reference_verification_status: Mapped[str] = mapped_column(String(20), nullable=False)

    # Evidence snapshots: exact decimal strings, never floats.
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    warnings_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    references_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # SHA-256 over the canonical input + result snapshot, for reproducibility checks.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    calculated_by: Mapped[str | None] = mapped_column(String(200))
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    submitted_by: Mapped[str | None] = mapped_column(String(200))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_notes: Mapped[str | None] = mapped_column(Text)
    rejected_by: Mapped[str | None] = mapped_column(String(200))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    supersedes_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="RESTRICT"),
        index=True,
    )
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return (
            "<CalculationRun("
            f"module_code='{self.module_code}', "
            f"calculation_key='{self.calculation_key}', "
            f"revision_number={self.revision_number}, "
            f"approval_status='{self.approval_status}'"
            ")>"
        )


__all__ = ["CalculationRun", "EngineeringCalculationType"]
