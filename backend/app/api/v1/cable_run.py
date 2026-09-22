"""
Persisted cable sizing runs (EOS-06, Master Prompt v2.1 item 15).

POST calculates and stores a new revision; GET endpoints return the frozen
evidence. There is no delete: runs are audit records.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.authentication import CurrentSession
from app.api.dependencies import DatabaseSession
from app.repositories.calculation_run import CalculationRunRepository
from app.repositories.project import ProjectRepository
from app.schemas.calculation_run import (
    CableRunCreateRequest,
    CableRunResponse,
    CalculationRunDetail,
    CalculationRunListResponse,
    CalculationRunSummary,
)
from app.services.calculation_run import (
    CABLE_MODULE_CODE,
    CableRunService,
    project_summaries,
    with_project,
)
from app.services.project import ProjectConflictError, ProjectNotFoundError, ProjectService

router = APIRouter(
    prefix="/electrical/cable/runs",
    tags=["Electrical Cable Sizing"],
)


def get_service(db: DatabaseSession) -> CableRunService:
    return CableRunService(CalculationRunRepository(db), ProjectService(ProjectRepository(db)))


async def revision_in_scope(
    db: DatabaseSession, identity: CurrentSession, revision_id: UUID
) -> None:
    """A run filter may only name a revision of the caller's own organization."""

    try:
        await ProjectService(ProjectRepository(db)).get_revision(
            identity.organization.id, revision_id
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "",
    response_model=CableRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cable_run(
    payload: CableRunCreateRequest,
    db: DatabaseSession,
    response: Response,
    identity: CurrentSession,
) -> CableRunResponse:
    """Calculate a cable study and persist it as a new run revision."""

    service = get_service(db)
    try:
        run, result, created = await service.create(
            payload,
            calculated_by=identity.label,
            organization_id=identity.organization.id,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProjectConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if not created:
        # A11: the latest revision already holds this exact evidence.
        response.status_code = status.HTTP_200_OK

    summaries = await project_summaries(service.projects, identity.organization.id, [run])

    return CableRunResponse(
        run=with_project(CalculationRunSummary.model_validate(run), summaries),
        result=result,
    )


@router.get(
    "",
    response_model=CalculationRunListResponse,
)
async def list_cable_runs(
    db: DatabaseSession,
    identity: CurrentSession,
    calculation_key: str | None = Query(default=None, min_length=1, max_length=100),
    project_revision_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> CalculationRunListResponse:
    """List the cable runs of one scope: a project revision, or the runs outside any project."""

    if project_revision_id is not None:
        await revision_in_scope(db, identity, project_revision_id)

    service = get_service(db)
    if calculation_key is not None:
        runs = await service.list_for_key(calculation_key, project_revision_id=project_revision_id)
    else:
        runs = await service.list_recent(limit=limit, project_revision_id=project_revision_id)

    summaries = await project_summaries(service.projects, identity.organization.id, runs)

    return CalculationRunListResponse(
        items=[with_project(CalculationRunSummary.model_validate(run), summaries) for run in runs],
    )


@router.get(
    "/{run_id}",
    response_model=CalculationRunDetail,
)
async def get_cable_run(
    run_id: UUID,
    db: DatabaseSession,
    identity: CurrentSession,
) -> CalculationRunDetail:
    """Return one persisted cable run with its frozen snapshots."""

    service = get_service(db)
    run = await service.get(run_id)
    if run is None or run.module_code != CABLE_MODULE_CODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cable run {run_id} was not found",
        )

    summaries = await project_summaries(service.projects, identity.organization.id, [run])

    return with_project(CalculationRunDetail.model_validate(run), summaries)


__all__ = ["router"]
