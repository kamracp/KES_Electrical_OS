"""
API endpoint for HT panel engineering.
KESE-S2-M9
"""

from fastapi import APIRouter, HTTPException

from app.schemas.ht_panel import (
    HTPanelSizingRequest,
    HTPanelSizingResponse,
)
from app.services.ht_panel import HTPanelService


router = APIRouter(
    prefix="/electrical/ht-panel",
    tags=["Electrical HT Panel"],
)

_service = HTPanelService()


@router.post(
    "/calculate",
    response_model=HTPanelSizingResponse,
)
async def calculate_ht_panel(
    payload: HTPanelSizingRequest,
) -> HTPanelSizingResponse:
    try:
        result = _service.calculate_ht_panel_sizing(payload)
        return HTPanelSizingResponse.model_validate(result)

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    """Calculate one HT panel engineering arrangement."""

    result = _service.calculate_ht_panel_sizing(payload)

    return HTPanelSizingResponse.model_validate(result)


__all__ = [
    "router",
]
