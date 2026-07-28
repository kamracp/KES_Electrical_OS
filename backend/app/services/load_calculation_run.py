"""
Service layer for persistent electrical calculation runs.
KESE-S2-M3
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.models.load_calculation_run import (
    CalculationApprovalStatus,
    CalculationRunStatus,
    LoadCalculationRun,
)
from app.repositories.load_calculation_run import (
    LoadCalculationRunRepository,
)
from app.schemas.load_calculation_run import (
    LoadCalculationRunApprove,
    LoadCalculationRunComparisonResponse,
    LoadCalculationRunCreate,
    LoadCalculationRunReject,
    LoadCalculationRunSubmit,
)


class LoadCalculationRunService:
    """
    Application service for calculation-run persistence and audit.

    The service controls revision numbering, deterministic content
    hashing, workflow transitions and approved-run immutability.
    """

    def __init__(
        self,
        repository: LoadCalculationRunRepository,
    ) -> None:
        self.repository = repository

    async def create(
        self,
        payload: LoadCalculationRunCreate,
    ) -> LoadCalculationRun:
        """Create a new immutable-history calculation revision."""

        if not isinstance(
            payload,
            LoadCalculationRunCreate,
        ):
            raise TypeError(
                "payload must be a LoadCalculationRunCreate"
            )

        content_hash = self._build_content_hash(payload)

        duplicate_run = (
            await self.repository.get_latest_by_content_hash(
                content_hash
            )
        )

        if (
            duplicate_run is not None
            and duplicate_run.calculation_key
            == payload.calculation_key
        ):
            raise ValueError(
                "an identical calculation run already exists"
            )

        latest_revision = (
            await self.repository.get_latest_revision(
                payload.calculation_key
            )
        )

        revision_number = (
            await self.repository.get_next_revision_number(
                payload.calculation_key
            )
        )

        snapshot_data = payload.model_dump(
            mode="json",
        )

        calculated_at = datetime.now(timezone.utc)

        completed_at = (
            calculated_at
            if payload.run_status
            in {
                CalculationRunStatus.COMPLETED,
                CalculationRunStatus.FAILED,
            }
            else None
        )

        calculation_run = LoadCalculationRun(
            calculation_key=payload.calculation_key,
            revision_number=revision_number,
            calculation_type=(
                payload.calculation_type.value
            ),
            scenario=payload.scenario.value,
            run_status=payload.run_status.value,
            approval_status=(
                CalculationApprovalStatus.NOT_SUBMITTED.value
            ),
            engine_version=payload.engine_version,
            formula_version=payload.formula_version,
            input_snapshot=snapshot_data[
                "input_snapshot"
            ],
            result_snapshot=snapshot_data[
                "result_snapshot"
            ],
            assumptions_snapshot=snapshot_data[
                "assumptions_snapshot"
            ],
            warnings_snapshot=snapshot_data[
                "warnings_snapshot"
            ],
            standards_snapshot=snapshot_data[
                "standards_snapshot"
            ],
            content_hash=content_hash,
            calculated_by=payload.calculated_by,
            calculated_at=calculated_at,
            completed_at=completed_at,
            supersedes_run_id=(
                latest_revision.id
                if latest_revision is not None
                else None
            ),
            is_immutable=False,
            notes=payload.notes,
        )

        return await self.repository.create(
            calculation_run
        )

    async def get_by_id(
        self,
        run_id: UUID,
    ) -> LoadCalculationRun:
        """Return a calculation run or raise a lookup error."""

        if not isinstance(run_id, UUID):
            raise TypeError("run_id must be a UUID")

        calculation_run = (
            await self.repository.get_by_id(run_id)
        )

        if calculation_run is None:
            raise LookupError(
                "calculation run not found"
            )

        return calculation_run

    async def list_revision_history(
        self,
        calculation_key: str,
    ) -> list[LoadCalculationRun]:
        """Return all revisions for one calculation key."""

        normalized_key = calculation_key.strip()

        if not normalized_key:
            raise ValueError(
                "calculation_key must not be empty"
            )

        return (
            await self.repository.list_by_calculation_key(
                normalized_key
            )
        )

    async def list_pending_review(
        self,
    ) -> list[LoadCalculationRun]:
        """Return calculation runs awaiting review."""

        return (
            await self.repository.list_pending_review()
        )

    async def submit(
        self,
        run_id: UUID,
        payload: LoadCalculationRunSubmit,
    ) -> LoadCalculationRun:
        """Submit a completed calculation for engineering review."""

        if not isinstance(
            payload,
            LoadCalculationRunSubmit,
        ):
            raise TypeError(
                "payload must be a LoadCalculationRunSubmit"
            )

        calculation_run = await self.get_by_id(run_id)

        self._ensure_mutable(calculation_run)

        if (
            calculation_run.run_status
            != CalculationRunStatus.COMPLETED.value
        ):
            raise ValueError(
                "only completed calculation runs "
                "can be submitted"
            )

        if (
            calculation_run.approval_status
            != CalculationApprovalStatus.NOT_SUBMITTED.value
        ):
            raise ValueError(
                "calculation run has already entered "
                "the review workflow"
            )

        calculation_run.approval_status = (
            CalculationApprovalStatus.PENDING.value
        )
        calculation_run.submitted_by = (
            payload.submitted_by
        )
        calculation_run.submitted_at = datetime.now(
            timezone.utc
        )

        return await self.repository.save(
            calculation_run
        )

    async def approve(
        self,
        run_id: UUID,
        payload: LoadCalculationRunApprove,
    ) -> LoadCalculationRun:
        """Approve and permanently lock a calculation run."""

        if not isinstance(
            payload,
            LoadCalculationRunApprove,
        ):
            raise TypeError(
                "payload must be a LoadCalculationRunApprove"
            )

        calculation_run = await self.get_by_id(run_id)

        self._ensure_mutable(calculation_run)

        if (
            calculation_run.approval_status
            != CalculationApprovalStatus.PENDING.value
        ):
            raise ValueError(
                "only pending calculation runs "
                "can be approved"
            )

        approved_at = datetime.now(timezone.utc)

        calculation_run.approval_status = (
            CalculationApprovalStatus.APPROVED.value
        )
        calculation_run.approved_by = (
            payload.approved_by
        )
        calculation_run.approved_at = approved_at
        calculation_run.approval_notes = (
            payload.approval_notes
        )
        calculation_run.is_immutable = True

        return await self.repository.save(
            calculation_run
        )

    async def reject(
        self,
        run_id: UUID,
        payload: LoadCalculationRunReject,
    ) -> LoadCalculationRun:
        """Reject a calculation run under controlled review."""

        if not isinstance(
            payload,
            LoadCalculationRunReject,
        ):
            raise TypeError(
                "payload must be a LoadCalculationRunReject"
            )

        calculation_run = await self.get_by_id(run_id)

        self._ensure_mutable(calculation_run)

        if (
            calculation_run.approval_status
            != CalculationApprovalStatus.PENDING.value
        ):
            raise ValueError(
                "only pending calculation runs "
                "can be rejected"
            )

        calculation_run.approval_status = (
            CalculationApprovalStatus.REJECTED.value
        )
        calculation_run.rejected_by = (
            payload.rejected_by
        )
        calculation_run.rejected_at = datetime.now(
            timezone.utc
        )
        calculation_run.rejection_reason = (
            payload.rejection_reason
        )

        return await self.repository.save(
            calculation_run
        )

    async def compare(
        self,
        base_run_id: UUID,
        target_run_id: UUID,
    ) -> LoadCalculationRunComparisonResponse:
        """Compare inputs, results and audit data for two revisions."""

        if base_run_id == target_run_id:
            raise ValueError(
                "base and target runs must be different"
            )

        base_run = await self.get_by_id(base_run_id)
        target_run = await self.get_by_id(
            target_run_id
        )

        if (
            base_run.calculation_key
            != target_run.calculation_key
        ):
            raise ValueError(
                "calculation runs must have the same "
                "calculation_key"
            )

        audit_base = {
            "scenario": base_run.scenario,
            "run_status": base_run.run_status,
            "approval_status": (
                base_run.approval_status
            ),
            "engine_version": base_run.engine_version,
            "formula_version": (
                base_run.formula_version
            ),
            "assumptions_snapshot": (
                base_run.assumptions_snapshot
            ),
            "warnings_snapshot": (
                base_run.warnings_snapshot
            ),
            "standards_snapshot": (
                base_run.standards_snapshot
            ),
        }

        audit_target = {
            "scenario": target_run.scenario,
            "run_status": target_run.run_status,
            "approval_status": (
                target_run.approval_status
            ),
            "engine_version": (
                target_run.engine_version
            ),
            "formula_version": (
                target_run.formula_version
            ),
            "assumptions_snapshot": (
                target_run.assumptions_snapshot
            ),
            "warnings_snapshot": (
                target_run.warnings_snapshot
            ),
            "standards_snapshot": (
                target_run.standards_snapshot
            ),
        }

        return LoadCalculationRunComparisonResponse(
            calculation_key=base_run.calculation_key,
            base_run_id=base_run.id,
            base_revision_number=(
                base_run.revision_number
            ),
            target_run_id=target_run.id,
            target_revision_number=(
                target_run.revision_number
            ),
            input_differences=self._compare_values(
                base_run.input_snapshot,
                target_run.input_snapshot,
            ),
            result_differences=self._compare_values(
                base_run.result_snapshot,
                target_run.result_snapshot,
            ),
            audit_differences=self._compare_values(
                audit_base,
                audit_target,
            ),
        )

    @staticmethod
    def _ensure_mutable(
        calculation_run: LoadCalculationRun,
    ) -> None:
        """Prevent modification of an approved audit record."""

        if calculation_run.is_immutable:
            raise ValueError(
                "approved calculation runs are immutable"
            )

        if (
            calculation_run.approval_status
            == CalculationApprovalStatus.APPROVED.value
        ):
            raise ValueError(
                "approved calculation runs are immutable"
            )

    @staticmethod
    def _build_content_hash(
        payload: LoadCalculationRunCreate,
    ) -> str:
        """Build a deterministic SHA-256 engineering-content hash."""

        hash_payload = {
            "calculation_key": payload.calculation_key,
            "calculation_type": (
                payload.calculation_type.value
            ),
            "scenario": payload.scenario.value,
            "run_status": payload.run_status.value,
            "engine_version": payload.engine_version,
            "formula_version": payload.formula_version,
            "input_snapshot": payload.input_snapshot,
            "result_snapshot": payload.result_snapshot,
            "assumptions_snapshot": (
                payload.assumptions_snapshot
            ),
            "warnings_snapshot": (
                payload.warnings_snapshot
            ),
            "standards_snapshot": (
                payload.standards_snapshot
            ),
        }

        canonical_json = json.dumps(
            hash_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

        return hashlib.sha256(
            canonical_json.encode("utf-8")
        ).hexdigest()

    @classmethod
    def _compare_values(
        cls,
        base_value: Any,
        target_value: Any,
        *,
        path: str = "",
    ) -> dict[str, Any]:
        """Return changed values using stable dotted paths."""

        differences: dict[str, Any] = {}

        if (
            isinstance(base_value, dict)
            and isinstance(target_value, dict)
        ):
            keys = sorted(
                set(base_value) | set(target_value)
            )

            for key in keys:
                nested_path = (
                    f"{path}.{key}"
                    if path
                    else key
                )

                if key not in base_value:
                    differences[nested_path] = {
                        "base": None,
                        "target": target_value[key],
                    }
                    continue

                if key not in target_value:
                    differences[nested_path] = {
                        "base": base_value[key],
                        "target": None,
                    }
                    continue

                differences.update(
                    cls._compare_values(
                        base_value[key],
                        target_value[key],
                        path=nested_path,
                    )
                )

            return differences

        if base_value != target_value:
            differences[path or "value"] = {
                "base": base_value,
                "target": target_value,
            }

        return differences


__all__ = [
    "LoadCalculationRunService",
]