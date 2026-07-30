"""
Service layer for generator source-sizing calculations.
KESE-S2-M7
"""

from app.domain.electrical.sources.generator_engine import (
    calculate_generator_sizing as calculate_domain_generator_sizing,
)
from app.domain.electrical.sources.generator_results import (
    GeneratorSizingResult,
)
from app.schemas.generator_sizing import (
    GeneratorSizingRequest,
)


class GeneratorSizingService:
    """
    Application service for generator source sizing.

    The service converts a validated API schema into an immutable
    domain record and delegates calculation to the pure domain engine.
    """

    def calculate_generator_sizing(
        self,
        payload: GeneratorSizingRequest,
    ) -> GeneratorSizingResult:
        """Calculate one validated generator source arrangement."""

        if not isinstance(
            payload,
            GeneratorSizingRequest,
        ):
            raise TypeError(
                "payload must be a GeneratorSizingRequest"
            )

        return calculate_domain_generator_sizing(
            payload.to_domain()
        )


__all__ = [
    "GeneratorSizingService",
]
