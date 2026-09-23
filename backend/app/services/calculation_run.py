"""
Service that executes an engine and persists the run as frozen evidence.

The engine result is computed exactly as the stateless calculate endpoint
does; the service then snapshots input, result, warnings and references,
hashes them and stores one immutable CalculationRun revision.

A run may belong to the open revision of a project (EOS-01 b). The revision is checked against
the caller's organization before the engine runs, so a study that cannot be stored costs no
calculation; without a revision the run belongs to no project, as every run did before. Each
scope carries its own revision numbering and its own A11 reuse rule.
"""

import hashlib
import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.domain.electrical.jurisdiction.jurisdiction_profiles import get_profile
from app.models.calculation_run import CalculationRun, EngineeringCalculationType
from app.models.load_calculation_run import (
    CalculationApprovalStatus,
    CalculationRunStatus,
)
from app.repositories.calculation_run import CalculationRunRepository
from app.schemas.cable import CableSizingResponse
from app.schemas.calculation_run import (
    CableRunCreateRequest,
    CalculationRunSummary,
    FaultRunCreateRequest,
    LoadRunCreateRequest,
)
from app.schemas.fault import ShortCircuitStudyResponse
from app.schemas.load_demand import LoadGroupCalculationResponse
from app.schemas.project import ProjectRevisionSummary
from app.services.cable import CableSizingService
from app.services.fault import FaultCalculationService
from app.services.load_demand import LoadDemandService
from app.services.project import ProjectConflictError, ProjectService

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


LOAD_MODULE_CODE = "EOS-02"
# Bump whenever the load engine's method, rounding or reference handling changes.
LOAD_ENGINE_VERSION = "load-engine 0.1.0"


def content_hash(input_snapshot: dict[str, Any], result_snapshot: dict[str, Any]) -> str:
    """Return the SHA-256 of the canonical JSON of input and result."""

    canonical = json.dumps(
        {"input": input_snapshot, "result": result_snapshot},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def reusable_run(
    latest: CalculationRun | None,
    new_hash: str,
    engine_version: str,
) -> CalculationRun | None:
    """Return the latest revision when it already holds this exact evidence (A11).

    A new revision is created only when the evidence (input + result hash) or the
    engine version differs from the latest revision of the same study.
    """

    if latest is None:
        return None
    if latest.content_hash != new_hash or latest.engine_version != engine_version:
        return None
    return latest


async def resolve_run_scope(
    projects: ProjectService,
    organization_id: UUID,
    project_revision_id: UUID | None,
    jurisdiction_profile: str,
) -> UUID | None:
    """Return the revision a new run is stored under, or None for a run outside any project.

    A revision of another organization is not found; a revision that cannot take runs (an
    archived project, a revision that is no longer open) and a study designed under another
    jurisdiction profile than the project are conflicts.
    """

    if project_revision_id is None:
        return None
    project, revision = await projects.revision_for_new_run(organization_id, project_revision_id)
    if project.jurisdiction_profile != jurisdiction_profile:
        raise ProjectConflictError("The study's jurisdiction profile must match the project's.")
    return revision.id


async def project_summaries(
    projects: ProjectService,
    organization_id: UUID,
    runs: Sequence[CalculationRun],
) -> dict[UUID, ProjectRevisionSummary]:
    """Name the project and revision of every run in one query, keyed by revision id."""

    found = await projects.revision_summaries(
        organization_id,
        {run.project_revision_id for run in runs if run.project_revision_id is not None},
    )
    return {
        revision_id: ProjectRevisionSummary(
            revision_id=revision.id,
            revision_number=revision.revision_number,
            revision_label=revision.label,
            project_id=project.id,
            project_code=project.code,
            project_name=project.name,
        )
        for revision_id, (project, revision) in found.items()
    }


def run_is_visible(run: CalculationRun, summaries: dict[UUID, ProjectRevisionSummary]) -> bool:
    """Whether this run may be read by the caller the summaries were resolved for.

    A run outside any project is readable by every member of every organization, as it was
    before EOS-01 (b) - those runs carry no organization at all. A run of a project revision
    is readable only where that revision was named, and project_summaries names a revision
    only within the reader's own organization.
    """

    return run.project_revision_id is None or run.project_revision_id in summaries


def with_project[SummaryT: CalculationRunSummary](
    summary: SummaryT, summaries: dict[UUID, ProjectRevisionSummary]
) -> SummaryT:
    """Attach the project and revision names to a run summary or detail."""

    if summary.project_revision_id is None:
        return summary
    return summary.model_copy(update={"project": summaries.get(summary.project_revision_id)})


class CableRunService:
    """Calculate a cable study and persist it as a CalculationRun."""

    def __init__(self, repository: CalculationRunRepository, projects: ProjectService) -> None:
        self.repository = repository
        self.projects = projects
        self.engine_service = CableSizingService()

    async def create(
        self,
        payload: CableRunCreateRequest,
        *,
        calculated_by: str,
        organization_id: UUID,
    ) -> tuple[CalculationRun, CableSizingResponse, bool]:
        """Run the engine and freeze the evidence; False flag = latest revision reused (A11)."""

        project_revision_id = await resolve_run_scope(
            self.projects,
            organization_id,
            payload.project_revision_id,
            str(payload.study.jurisdiction_profile),
        )
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
        evidence_hash = content_hash(input_snapshot, result_snapshot)
        latest = await self.repository.get_latest_revision(
            CABLE_MODULE_CODE,
            calculation_key,
            project_revision_id=project_revision_id,
        )
        existing = reusable_run(latest, evidence_hash, CABLE_ENGINE_VERSION)
        if existing is not None:
            return existing, response, False

        revision = await self.repository.get_next_revision_number(
            CABLE_MODULE_CODE,
            calculation_key,
            project_revision_id=project_revision_id,
        )

        run = CalculationRun(
            project_revision_id=project_revision_id,
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
            content_hash=evidence_hash,
            calculated_by=calculated_by,
            is_immutable=False,
            notes=payload.notes,
        )
        stored = await self.repository.create(run)
        return stored, response, True

    async def get(self, run_id: UUID) -> CalculationRun | None:
        """Return one run by id (any module)."""

        return await self.repository.get_by_id(run_id)

    async def list_for_key(
        self, calculation_key: str, *, project_revision_id: UUID | None = None
    ) -> list[CalculationRun]:
        """Return every cable run revision for a study code in one scope, newest first."""

        return await self.repository.list_by_calculation_key(
            CABLE_MODULE_CODE,
            calculation_key,
            project_revision_id=project_revision_id,
        )

    async def list_recent(
        self, limit: int = 20, *, project_revision_id: UUID | None = None
    ) -> list[CalculationRun]:
        """Return the most recent cable runs of one scope."""

        return await self.repository.list_recent(
            CABLE_MODULE_CODE, limit=limit, project_revision_id=project_revision_id
        )


class FaultRunService:
    """Calculate a short-circuit study and persist it as a CalculationRun."""

    def __init__(self, repository: CalculationRunRepository, projects: ProjectService) -> None:
        self.repository = repository
        self.projects = projects
        self.engine_service = FaultCalculationService()

    async def create(
        self,
        payload: FaultRunCreateRequest,
        *,
        calculated_by: str,
        organization_id: UUID,
    ) -> tuple[CalculationRun, ShortCircuitStudyResponse, bool]:
        """Run the engine and freeze the evidence; False flag = latest revision reused (A11)."""

        project_revision_id = await resolve_run_scope(
            self.projects,
            organization_id,
            payload.project_revision_id,
            str(payload.study.jurisdiction_profile),
        )
        result = self.engine_service.calculate_short_circuit(payload.study)
        response = ShortCircuitStudyResponse.from_domain(result)

        input_snapshot = payload.study.model_dump(mode="json")
        # The JSON-mode dump is the single source for every stored value, so the
        # run row always matches what the API returns.
        result_snapshot = response.model_dump(mode="json")
        references_snapshot = {name: result_snapshot[name] for name in _FAULT_REFERENCE_FIELDS}
        calculation_key = payload.study.code
        evidence_hash = content_hash(input_snapshot, result_snapshot)
        latest = await self.repository.get_latest_revision(
            FAULT_MODULE_CODE,
            calculation_key,
            project_revision_id=project_revision_id,
        )
        existing = reusable_run(latest, evidence_hash, FAULT_ENGINE_VERSION)
        if existing is not None:
            return existing, response, False

        revision = await self.repository.get_next_revision_number(
            FAULT_MODULE_CODE,
            calculation_key,
            project_revision_id=project_revision_id,
        )

        run = CalculationRun(
            project_revision_id=project_revision_id,
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
            content_hash=evidence_hash,
            calculated_by=calculated_by,
            is_immutable=False,
            notes=payload.notes,
        )
        stored = await self.repository.create(run)
        return stored, response, True

    async def get(self, run_id: UUID) -> CalculationRun | None:
        """Return one run by id (any module)."""

        return await self.repository.get_by_id(run_id)

    async def list_for_key(
        self, calculation_key: str, *, project_revision_id: UUID | None = None
    ) -> list[CalculationRun]:
        """Return every fault run revision for a study code in one scope, newest first."""

        return await self.repository.list_by_calculation_key(
            FAULT_MODULE_CODE,
            calculation_key,
            project_revision_id=project_revision_id,
        )

    async def list_recent(
        self, limit: int = 20, *, project_revision_id: UUID | None = None
    ) -> list[CalculationRun]:
        """Return the most recent fault runs of one scope."""

        return await self.repository.list_recent(
            FAULT_MODULE_CODE, limit=limit, project_revision_id=project_revision_id
        )


class LoadRunService:
    """Calculate a load schedule and persist it as a CalculationRun."""

    def __init__(self, repository: CalculationRunRepository, projects: ProjectService) -> None:
        self.repository = repository
        self.projects = projects
        self.engine_service = LoadDemandService()

    async def create(
        self,
        payload: LoadRunCreateRequest,
        *,
        calculated_by: str,
        organization_id: UUID,
    ) -> tuple[CalculationRun, LoadGroupCalculationResponse, bool]:
        """Run the engine and freeze the evidence; False flag = latest revision reused (A11)."""

        project_revision_id = await resolve_run_scope(
            self.projects,
            organization_id,
            payload.project_revision_id,
            str(payload.study.jurisdiction_profile),
        )
        result = self.engine_service.calculate_load_group(payload.study)
        response = LoadGroupCalculationResponse.from_domain(
            result,
            jurisdiction_profile=payload.study.jurisdiction_profile,
        )

        input_snapshot = payload.study.model_dump(mode="json")
        result_snapshot = response.model_dump(mode="json")
        # The load engine cites no reference of its own, so the run carries the reference
        # state of the chosen jurisdiction profile instead - the same registry entry the
        # cable and fault engines read (GAP-015 removed the only unreferenced limits).
        verification_status = str(
            get_profile(payload.study.jurisdiction_profile).reference_data_status
        )
        references_snapshot = {
            "jurisdiction_profile": result_snapshot["jurisdiction_profile"],
            "reference_verification_status": verification_status,
            "assumptions": result_snapshot["assumptions"],
        }
        calculation_key = payload.study.code
        evidence_hash = content_hash(input_snapshot, result_snapshot)
        latest = await self.repository.get_latest_revision(
            LOAD_MODULE_CODE,
            calculation_key,
            project_revision_id=project_revision_id,
        )
        existing = reusable_run(latest, evidence_hash, LOAD_ENGINE_VERSION)
        if existing is not None:
            return existing, response, False

        revision = await self.repository.get_next_revision_number(
            LOAD_MODULE_CODE,
            calculation_key,
            project_revision_id=project_revision_id,
        )

        run = CalculationRun(
            project_revision_id=project_revision_id,
            module_code=LOAD_MODULE_CODE,
            calculation_type=EngineeringCalculationType.LOAD_DEMAND.value,
            calculation_key=calculation_key,
            revision_number=revision,
            run_status=CalculationRunStatus.COMPLETED.value,
            approval_status=CalculationApprovalStatus.NOT_SUBMITTED.value,
            engine_version=LOAD_ENGINE_VERSION,
            design_check_status=str(result_snapshot["status"]),
            jurisdiction_profile=str(result_snapshot["jurisdiction_profile"]),
            reference_verification_status=verification_status,
            input_snapshot=input_snapshot,
            result_snapshot=result_snapshot,
            warnings_snapshot=list(result_snapshot.get("warnings", [])),
            references_snapshot=references_snapshot,
            content_hash=evidence_hash,
            calculated_by=calculated_by,
            is_immutable=False,
            notes=payload.notes,
        )
        stored = await self.repository.create(run)
        return stored, response, True

    async def get(self, run_id: UUID) -> CalculationRun | None:
        """Return one run by id (any module)."""

        return await self.repository.get_by_id(run_id)

    async def list_for_key(
        self, calculation_key: str, *, project_revision_id: UUID | None = None
    ) -> list[CalculationRun]:
        """Return every load run revision for a study code in one scope, newest first."""

        return await self.repository.list_by_calculation_key(
            LOAD_MODULE_CODE,
            calculation_key,
            project_revision_id=project_revision_id,
        )

    async def list_recent(
        self, limit: int = 20, *, project_revision_id: UUID | None = None
    ) -> list[CalculationRun]:
        """Return the most recent load runs of one scope."""

        return await self.repository.list_recent(
            LOAD_MODULE_CODE, limit=limit, project_revision_id=project_revision_id
        )


__all__ = [
    "CABLE_ENGINE_VERSION",
    "CABLE_MODULE_CODE",
    "FAULT_ENGINE_VERSION",
    "FAULT_MODULE_CODE",
    "LOAD_ENGINE_VERSION",
    "LOAD_MODULE_CODE",
    "CableRunService",
    "FaultRunService",
    "LoadRunService",
    "content_hash",
    "project_summaries",
    "resolve_run_scope",
    "reusable_run",
    "run_is_visible",
    "with_project",
]
