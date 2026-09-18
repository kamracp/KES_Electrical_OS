"""
API schemas for persisted engineering calculation runs (any module).

A run summary is the traceability record a study page shows (run ID, engine
version, profile, reference status, hash, timestamps, approval state); the
detail adds the frozen snapshots a report consumes.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.cable import CableSizingRequest, CableSizingResponse
from app.schemas.fault import ShortCircuitStudyRequest, ShortCircuitStudyResponse


class _ResponseBase(BaseModel):
    """Shared configuration for run responses built from ORM rows."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class CalculationRunSummary(_ResponseBase):
    """Traceability record of one persisted run."""

    id: UUID
    module_code: str
    calculation_type: str
    calculation_key: str
    revision_number: int
    run_status: str
    approval_status: str
    engine_version: str
    design_check_status: str
    jurisdiction_profile: str
    reference_verification_status: str
    content_hash: str
    calculated_by: str | None
    calculated_at: datetime
    created_at: datetime
    is_immutable: bool
    supersedes_run_id: UUID | None
    notes: str | None


class CalculationRunDetail(CalculationRunSummary):
    """Run summary plus the frozen evidence snapshots."""

    input_snapshot: dict[str, Any]
    result_snapshot: dict[str, Any]
    warnings_snapshot: list[dict[str, Any]]
    references_snapshot: dict[str, Any]


class CalculationRunListResponse(BaseModel):
    """A page of run summaries, newest first."""

    model_config = ConfigDict(extra="forbid")

    items: list[CalculationRunSummary]


class CableRunCreateRequest(BaseModel):
    """Calculate a cable study and persist the result as a run."""

    model_config = ConfigDict(extra="forbid")

    study: CableSizingRequest
    calculated_by: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class CableRunResponse(BaseModel):
    """The persisted run record together with the typed cable result."""

    model_config = ConfigDict(extra="forbid")

    run: CalculationRunSummary
    result: CableSizingResponse


class FaultRunCreateRequest(BaseModel):
    """Calculate a short-circuit study and persist the result as a run."""

    model_config = ConfigDict(extra="forbid")

    study: ShortCircuitStudyRequest
    calculated_by: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class FaultRunResponse(BaseModel):
    """The persisted run record together with the typed short-circuit result."""

    model_config = ConfigDict(extra="forbid")

    run: CalculationRunSummary
    result: ShortCircuitStudyResponse


__all__ = [
    "CableRunCreateRequest",
    "CableRunResponse",
    "CalculationRunDetail",
    "CalculationRunListResponse",
    "CalculationRunSummary",
    "FaultRunCreateRequest",
    "FaultRunResponse",
]
