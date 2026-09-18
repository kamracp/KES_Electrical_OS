"""
Persisted short-circuit study runs (EOS-04, Master Prompt v2.1 item 16b).

POST calculates and stores a new revision; GET endpoints return the frozen
evidence. There is no delete: runs are audit records.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.dependencies import DatabaseSession
from app.repositories.calculation_run import CalculationRunRepository
from app.schemas.calculation_run import (
    CalculationRunDetail,
    CalculationRunListResponse,
    CalculationRunSummary,
    FaultRunCreateRequest,
    FaultRunResponse,
)
from app.services.calculation_run import FAULT_MODULE_CODE, FaultRunService

router = APIRouter(
    prefix="/electrical/fault/runs",
    tags=["Electrical Fault Study"],
)


def get_service(db: DatabaseSession) -> FaultRunService:
    return FaultRunService(CalculationRunRepository(db))


@router.post(
    "",
    response_model=FaultRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_fault_run(
    payload: FaultRunCreateRequest,
    db: DatabaseSession,
    response: Response,
) -> FaultRunResponse:
    """Calculate a short-circuit study and persist it as a new run revision."""

    try:
        run, result, created = await get_service(db).create(payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if not created:
        # A11: the latest revision already holds this exact evidence.
        response.status_code = status.HTTP_200_OK

    return FaultRunResponse(
        run=CalculationRunSummary.model_validate(run),
        result=result,
    )


@router.get(
    "",
    response_model=CalculationRunListResponse,
)
async def list_fault_runs(
    db: DatabaseSession,
    calculation_key: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
) -> CalculationRunListResponse:
    """List fault runs: every revision of one study code, or the most recent runs."""

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
async def get_fault_run(
    run_id: UUID,
    db: DatabaseSession,
) -> CalculationRunDetail:
    """Return one persisted fault run with its frozen snapshots."""

    run = await get_service(db).get(run_id)
    if run is None or run.module_code != FAULT_MODULE_CODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fault run {run_id} was not found",
        )

    return CalculationRunDetail.model_validate(run)


__all__ = ["router"]
