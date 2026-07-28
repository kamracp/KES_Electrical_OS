"""
API endpoints for persistent electrical calculation runs.
KESE-S2-M3
"""

from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)

from app.api.dependencies import DatabaseSession
from app.repositories.load_calculation_run import (
    LoadCalculationRunRepository,
)
from app.schemas.load_calculation_run import (
    LoadCalculationRunApprove,
    LoadCalculationRunComparisonResponse,
    LoadCalculationRunCreate,
    LoadCalculationRunReject,
    LoadCalculationRunResponse,
    LoadCalculationRunSubmit,
)
from app.services.load_calculation_run import (
    LoadCalculationRunService,
)


router = APIRouter(
    prefix="/electrical/calculation-runs",
    tags=["Electrical Calculation Runs"],
)


def get_service(
    db: DatabaseSession,
) -> LoadCalculationRunService:
    """Create a calculation-run service for the request."""

    return LoadCalculationRunService(
        LoadCalculationRunRepository(db)
    )


def raise_service_error(
    error: Exception,
) -> None:
    """Convert controlled service errors into API responses."""

    if isinstance(error, LookupError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    if isinstance(error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    raise error


@router.post(
    "/",
    response_model=LoadCalculationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_calculation_run(
    payload: LoadCalculationRunCreate,
    db: DatabaseSession,
) -> LoadCalculationRunResponse:
    """Persist a new electrical calculation revision."""

    try:
        calculation_run = await get_service(db).create(
            payload
        )
    except (LookupError, ValueError) as error:
        raise_service_error(error)

    return LoadCalculationRunResponse.model_validate(
        calculation_run
    )


@router.get(
    "/pending-review",
    response_model=list[LoadCalculationRunResponse],
)
async def list_pending_review(
    db: DatabaseSession,
) -> list[LoadCalculationRunResponse]:
    """Return calculation runs awaiting engineering review."""

    calculation_runs = (
        await get_service(db).list_pending_review()
    )

    return [
        LoadCalculationRunResponse.model_validate(
            calculation_run
        )
        for calculation_run in calculation_runs
    ]


@router.get(
    "/history/{calculation_key}",
    response_model=list[LoadCalculationRunResponse],
)
async def list_revision_history(
    calculation_key: str,
    db: DatabaseSession,
) -> list[LoadCalculationRunResponse]:
    """Return complete revision history for a calculation key."""

    try:
        calculation_runs = (
            await get_service(
                db
            ).list_revision_history(
                calculation_key
            )
        )
    except ValueError as error:
        raise_service_error(error)

    return [
        LoadCalculationRunResponse.model_validate(
            calculation_run
        )
        for calculation_run in calculation_runs
    ]


@router.get(
    "/compare",
    response_model=LoadCalculationRunComparisonResponse,
)
async def compare_calculation_runs(
    db: DatabaseSession,
    base_run_id: UUID = Query(...),
    target_run_id: UUID = Query(...),
) -> LoadCalculationRunComparisonResponse:
    """Compare two revisions of the same calculation."""

    try:
        return await get_service(db).compare(
            base_run_id,
            target_run_id,
        )
    except (LookupError, ValueError) as error:
        raise_service_error(error)


@router.get(
    "/{run_id}",
    response_model=LoadCalculationRunResponse,
)
async def get_calculation_run(
    run_id: UUID,
    db: DatabaseSession,
) -> LoadCalculationRunResponse:
    """Return one calculation run by UUID."""

    try:
        calculation_run = await get_service(db).get_by_id(
            run_id
        )
    except LookupError as error:
        raise_service_error(error)

    return LoadCalculationRunResponse.model_validate(
        calculation_run
    )


@router.post(
    "/{run_id}/submit",
    response_model=LoadCalculationRunResponse,
)
async def submit_calculation_run(
    run_id: UUID,
    payload: LoadCalculationRunSubmit,
    db: DatabaseSession,
) -> LoadCalculationRunResponse:
    """Submit a completed calculation run for review."""

    try:
        calculation_run = await get_service(db).submit(
            run_id,
            payload,
        )
    except (LookupError, ValueError) as error:
        raise_service_error(error)

    return LoadCalculationRunResponse.model_validate(
        calculation_run
    )


@router.post(
    "/{run_id}/approve",
    response_model=LoadCalculationRunResponse,
)
async def approve_calculation_run(
    run_id: UUID,
    payload: LoadCalculationRunApprove,
    db: DatabaseSession,
) -> LoadCalculationRunResponse:
    """Approve and permanently lock a calculation run."""

    try:
        calculation_run = await get_service(db).approve(
            run_id,
            payload,
        )
    except (LookupError, ValueError) as error:
        raise_service_error(error)

    return LoadCalculationRunResponse.model_validate(
        calculation_run
    )


@router.post(
    "/{run_id}/reject",
    response_model=LoadCalculationRunResponse,
)
async def reject_calculation_run(
    run_id: UUID,
    payload: LoadCalculationRunReject,
    db: DatabaseSession,
) -> LoadCalculationRunResponse:
    """Reject a calculation run under engineering review."""

    try:
        calculation_run = await get_service(db).reject(
            run_id,
            payload,
        )
    except (LookupError, ValueError) as error:
        raise_service_error(error)

    return LoadCalculationRunResponse.model_validate(
        calculation_run
    )


__all__ = [
    "router",
]