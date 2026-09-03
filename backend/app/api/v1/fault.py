"""
API endpoint for short-circuit and earth-fault engineering.

KESE-S2-M15
"""

from fastapi import APIRouter, HTTPException

from app.schemas.fault import (
    ShortCircuitStudyRequest,
    ShortCircuitStudyResponse,
)
from app.services.fault import FaultCalculationService

router = APIRouter(
    prefix="/electrical/fault",
    tags=["Electrical Fault Study"],
)

_service = FaultCalculationService()


@router.post(
    "/calculate",
    response_model=ShortCircuitStudyResponse,
)
async def calculate_short_circuit(
    payload: ShortCircuitStudyRequest,
) -> ShortCircuitStudyResponse:
    """Calculate one short-circuit or earth-fault study."""

    try:
        result = _service.calculate_short_circuit(payload)
        return ShortCircuitStudyResponse.from_domain(result)

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


__all__ = [
    "router",
]
