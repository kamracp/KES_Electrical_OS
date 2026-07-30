"""
Service layer for transformer source-sizing calculations.
KESE-S2-M5
"""

from kes_electrical_core.sources.engine import (
    calculate_transformer_sizing as calculate_domain_transformer_sizing,
)
from kes_electrical_core.sources.results import (
    TransformerSizingResult,
)
from app.schemas.transformer_sizing import (
    TransformerSizingRequest,
)


class TransformerSizingService:
    """
    Application service for transformer source sizing.

    The service converts a validated API schema into an immutable
    domain record and delegates the engineering calculation to the
    pure transformer-sizing domain engine.
    """

    def calculate_transformer_sizing(
        self,
        payload: TransformerSizingRequest,
    ) -> TransformerSizingResult:
        """Calculate one validated transformer source arrangement."""

        if not isinstance(
            payload,
            TransformerSizingRequest,
        ):
            raise TypeError(
                "payload must be a TransformerSizingRequest"
            )

        return calculate_domain_transformer_sizing(
            payload.to_domain()
        )


__all__ = [
    "TransformerSizingService",
]
