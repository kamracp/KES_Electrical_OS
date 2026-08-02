"""
API endpoint for LT PCC / Main Panel engineering.
KESE-S2-M10
"""

from fastapi import APIRouter, HTTPException

from app.schemas.lt_pcc import (
    LTPCCSizingRequest,
    LTPCCSizingResponse,
)
from app.services.lt_pcc import LTPCCService


router = APIRouter(
    prefix="/electrical/lt-pcc",
    tags=["Electrical LT PCC"],
)

_service = LTPCCService()


@router.post(
    "/calculate",
    response_model=LTPCCSizingResponse,
)
async def calculate_lt_pcc(
    payload: LTPCCSizingRequest,
) -> LTPCCSizingResponse:
    """Calculate one LT PCC engineering arrangement."""

    try:
        result = _service.calculate_lt_pcc_sizing(payload)

        return LTPCCSizingResponse.model_validate(result)

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


__all__ = [
    "router",
]
