"""
API endpoints for electrical load and demand calculations.
KESE-S2-M2
"""

from fastapi import APIRouter, status

from app.schemas.load_demand import (
    LoadCalculationRequest,
    LoadCalculationResponse,
    LoadGroupCalculationRequest,
    LoadGroupCalculationResponse,
)
from app.services.load_demand import LoadDemandService

router = APIRouter(
    prefix="/electrical/load-demand",
    tags=["Electrical Load & Demand"],
)

_service = LoadDemandService()


@router.post(
    "/calculate",
    response_model=LoadCalculationResponse,
    status_code=status.HTTP_200_OK,
)
def calculate_single_load(
    payload: LoadCalculationRequest,
) -> LoadCalculationResponse:
    """Calculate one electrical load."""

    result = _service.calculate_load(payload)

    return LoadCalculationResponse.model_validate(result)


@router.post(
    "/calculate-group",
    response_model=LoadGroupCalculationResponse,
    status_code=status.HTTP_200_OK,
)
def calculate_load_group(
    payload: LoadGroupCalculationRequest,
) -> LoadGroupCalculationResponse:
    """Calculate and aggregate one electrical load group."""

    result = _service.calculate_load_group(payload)

    return LoadGroupCalculationResponse.model_validate(result)


__all__ = [
    "router",
]