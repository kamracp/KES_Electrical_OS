"""
Persisted cable sizing runs (EOS-06, Master Prompt v2.1 item 15).

POST calculates and stores a new revision; GET endpoints return the frozen
evidence. There is no delete: runs are audit records.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DatabaseSession
from app.repositories.calculation_run import CalculationRunRepository
from app.schemas.calculation_run import (
    CableRunCreateRequest,
    CableRunResponse,
    CalculationRunDetail,
    CalculationRunListResponse,
    CalculationRunSummary,
)
from app.services.calculation_run import CABLE_MODULE_CODE, CableRunService

router = APIRouter(
    prefix="/electrical/cable/runs",
    tags=["Electrical Cable Sizing"],
)


def get_service(db: DatabaseSession) -> CableRunService:
    return CableRunService(CalculationRunRepository(db))


@router.post(
    "",
    response_model=CableRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cable_run(
    payload: CableRunCreateRequest,
    db: DatabaseSession,
) -> CableRunResponse:
    """Calculate a cable study and persist it as a new run revision."""

    try:
        run, result = await get_service(db).create(payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return CableRunResponse(
        run=CalculationRunSummary.model_validate(run),
        result=result,
    )


@router.get(
    "",
    response_model=CalculationRunListResponse,
)
async def list_cable_runs(
    db: DatabaseSession,
    calculation_key: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
) -> CalculationRunListResponse:
    """List cable runs: every revision of one study code, or the most recent runs."""

    service = get_service(db)
    if calculation_key is not None:
        runs = await service.list_for_key(calculation_key)
    else:
        runs = await service.list_recent(limit=limit)

    return CalculationRunListResponse(
        items=[CalculationRunSummary.model_validate(run) for run in runs],
    )


@router.get(
    "/{run_id}",
    response_model=CalculationRunDetail,
)
async def get_cable_run(
    run_id: UUID,
    db: DatabaseSession,
) -> CalculationRunDetail:
    """Return one persisted cable run with its frozen snapshots."""

    run = await get_service(db).get(run_id)
    if run is None or run.module_code != CABLE_MODULE_CODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cable run {run_id} was not found",
        )

    return CalculationRunDetail.model_validate(run)


__all__ = ["router"]
