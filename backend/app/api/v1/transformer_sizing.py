"""
API endpoint for transformer source-sizing calculations.
KESE-S2-M5
"""

from fastapi import APIRouter, status

from app.schemas.transformer_sizing import (
    TransformerSizingRequest,
    TransformerSizingResponse,
)
from app.services.transformer_sizing import (
    TransformerSizingService,
)


router = APIRouter(
    prefix="/electrical/transformer-sizing",
    tags=["Electrical Transformer Sizing"],
)

_service = TransformerSizingService()


@router.post(
    "/calculate",
    response_model=TransformerSizingResponse,
    status_code=status.HTTP_200_OK,
)
def calculate_transformer_sizing(
    payload: TransformerSizingRequest,
) -> TransformerSizingResponse:
    """Calculate a transformer source-sizing arrangement."""

    result = _service.calculate_transformer_sizing(payload)

    return TransformerSizingResponse.model_validate(result)


__all__ = [
    "router",
]
