"""
Service that executes an engine and persists the run as frozen evidence.

The engine result is computed exactly as the stateless calculate endpoint
does; the service then snapshots input, result, warnings and references,
hashes them and stores one immutable CalculationRun revision.
"""

import hashlib
import json
from typing import Any
from uuid import UUID

from app.models.calculation_run import CalculationRun, EngineeringCalculationType
from app.models.load_calculation_run import (
    CalculationApprovalStatus,
    CalculationRunStatus,
)
from app.repositories.calculation_run import CalculationRunRepository
from app.schemas.cable import CableSizingResponse
from app.schemas.calculation_run import CableRunCreateRequest, FaultRunCreateRequest
from app.schemas.fault import ShortCircuitStudyResponse
from app.services.cable import CableSizingService
from app.services.fault import FaultCalculationService

CABLE_MODULE_CODE = "EOS-06"
# Bump whenever the cable engine's method, rounding or reference handling changes.
CABLE_ENGINE_VERSION = "cable-engine 0.1.0"

FAULT_MODULE_CODE = "EOS-04"
# Bump whenever the fault engine's method, rounding or reference handling changes.
FAULT_ENGINE_VERSION = "fault-engine 0.1.0"
# Result fields frozen into the references snapshot of a fault run.
_FAULT_REFERENCE_FIELDS = (
    "standard_reference",
    "earth_current_reference",
    "reference_source",
    "jurisdiction_profile",
    "reference_verification_status",
)


def content_hash(input_snapshot: dict[str, Any], result_snapshot: dict[str, Any]) -> str:
    """Return the SHA-256 of the canonical JSON of input and result."""

    canonical = json.dumps(
        {"input": input_snapshot, "result": result_snapshot},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CableRunService:
    """Calculate a cable study and persist it as a CalculationRun."""

    def __init__(self, repository: CalculationRunRepository) -> None:
        self.repository = repository
        self.engine_service = CableSizingService()

    async def create(
        self,
        payload: CableRunCreateRequest,
    ) -> tuple[CalculationRun, CableSizingResponse]:
        """Run the engine, freeze the evidence and store a new revision."""

        result = self.engine_service.calculate_cable_sizing(payload.study)
        response = CableSizingResponse.from_domain(result)

        input_snapshot = payload.study.model_dump(mode="json")
        result_snapshot = response.model_dump(mode="json")
        references_snapshot = {
            "standard_reference": response.standard_reference,
            "ampacity_reference": response.ampacity_reference,
            "reference_source": response.reference_source,
            "jurisdiction_profile": response.jurisdiction_profile,
            "reference_verification_status": response.reference_verification_status,
        }
        calculation_key = payload.study.code
        revision = await self.repository.get_next_revision_number(
            CABLE_MODULE_CODE,
            calculation_key,
        )

        run = CalculationRun(
            module_code=CABLE_MODULE_CODE,
            calculation_type=EngineeringCalculationType.CABLE_SIZING.value,
            calculation_key=calculation_key,
            revision_number=revision,
            run_status=CalculationRunStatus.COMPLETED.value,
            approval_status=CalculationApprovalStatus.NOT_SUBMITTED.value,
            engine_version=CABLE_ENGINE_VERSION,
            design_check_status=str(response.status),
            jurisdiction_profile=str(response.jurisdiction_profile),
            reference_verification_status=str(response.reference_verification_status),
            input_snapshot=input_snapshot,
            result_snapshot=result_snapshot,
            warnings_snapshot=list(result_snapshot.get("warnings", [])),
            references_snapshot=references_snapshot,
            content_hash=content_hash(input_snapshot, result_snapshot),
            calculated_by=payload.calculated_by,
            is_immutable=False,
            notes=payload.notes,
        )
        stored = await self.repository.create(run)
        return stored, response

    async def get(self, run_id: UUID) -> CalculationRun | None:
        """Return one run by id (any module)."""

        return await self.repository.get_by_id(run_id)

    async def list_for_key(self, calculation_key: str) -> list[CalculationRun]:
        """Return every cable run revision for a study code, newest first."""

        return await self.repository.list_by_calculation_key(
            CABLE_MODULE_CODE,
            calculation_key,
        )

    async def list_recent(self, limit: int = 20) -> list[CalculationRun]:
        """Return the most recent cable runs."""

        return await self.repository.list_recent(CABLE_MODULE_CODE, limit=limit)


class FaultRunService:
    """Calculate a short-circuit study and persist it as a CalculationRun."""

    def __init__(self, repository: CalculationRunRepository) -> None:
        self.repository = repository
        self.engine_service = FaultCalculationService()

    async def create(
        self,
        payload: FaultRunCreateRequest,
    ) -> tuple[CalculationRun, ShortCircuitStudyResponse]:
        """Run the engine, freeze the evidence and store a new revision."""

        result = self.engine_service.calculate_short_circuit(payload.study)
        response = ShortCircuitStudyResponse.from_domain(result)

        input_snapshot = payload.study.model_dump(mode="json")
        # The JSON-mode dump is the single source for every stored value, so the
        # run row always matches what the API returns.
        result_snapshot = response.model_dump(mode="json")
        references_snapshot = {name: result_snapshot[name] for name in _FAULT_REFERENCE_FIELDS}
        calculation_key = payload.study.code
        revision = await self.repository.get_next_revision_number(
            FAULT_MODULE_CODE,
            calculation_key,
        )

        run = CalculationRun(
            module_code=FAULT_MODULE_CODE,
            calculation_type=EngineeringCalculationType.SHORT_CIRCUIT.value,
            calculation_key=calculation_key,
            revision_number=revision,
            run_status=CalculationRunStatus.COMPLETED.value,
            approval_status=CalculationApprovalStatus.NOT_SUBMITTED.value,
            engine_version=FAULT_ENGINE_VERSION,
            design_check_status=str(result_snapshot["status"]),
            jurisdiction_profile=str(result_snapshot["jurisdiction_profile"]),
            reference_verification_status=str(result_snapshot["reference_verification_status"]),
            input_snapshot=input_snapshot,
            result_snapshot=result_snapshot,
            warnings_snapshot=list(result_snapshot.get("warnings", [])),
            references_snapshot=references_snapshot,
            content_hash=content_hash(input_snapshot, result_snapshot),
            calculated_by=payload.calculated_by,
            is_immutable=False,
            notes=payload.notes,
        )
        stored = await self.repository.create(run)
        return stored, response

    async def get(self, run_id: UUID) -> CalculationRun | None:
        """Return one run by id (any module)."""

        return await self.repository.get_by_id(run_id)

    async def list_for_key(self, calculation_key: str) -> list[CalculationRun]:
        """Return every fault run revision for a study code, newest first."""

        return await self.repository.list_by_calculation_key(
            FAULT_MODULE_CODE,
            calculation_key,
        )

    async def list_recent(self, limit: int = 20) -> list[CalculationRun]:
        """Return the most recent fault runs."""

        return await self.repository.list_recent(FAULT_MODULE_CODE, limit=limit)


__all__ = [
    "CABLE_ENGINE_VERSION",
    "CABLE_MODULE_CODE",
    "FAULT_ENGINE_VERSION",
    "FAULT_MODULE_CODE",
    "CableRunService",
    "FaultRunService",
    "content_hash",
]
