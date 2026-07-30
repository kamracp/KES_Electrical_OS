"""
API endpoint for generator source-sizing calculations.
KESE-S2-M7
"""

from fastapi import APIRouter, status

from app.schemas.generator_sizing import (
    GeneratorSizingRequest,
    GeneratorSizingResponse,
)
from app.services.generator_sizing import (
    GeneratorSizingService,
)


router = APIRouter(
    prefix="/electrical/generator-sizing",
    tags=["Electrical Generator Sizing"],
)

_service = GeneratorSizingService()


@router.post(
    "/calculate",
    response_model=GeneratorSizingResponse,
    status_code=status.HTTP_200_OK,
)
def calculate_generator_sizing(
    payload: GeneratorSizingRequest,
) -> GeneratorSizingResponse:
    """Calculate a generator source-sizing arrangement."""

    result = _service.calculate_generator_sizing(payload)

    return GeneratorSizingResponse.model_validate(result)


__all__ = [
    "router",
]
