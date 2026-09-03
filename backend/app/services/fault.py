"""
Service layer for short-circuit and earth-fault engineering.

KESE-S2-M15
"""

from app.domain.electrical.fault import (
    ShortCircuitStudyResult,
)
from app.domain.electrical.fault import (
    calculate_short_circuit as calculate_domain_short_circuit,
)
from app.schemas.fault import ShortCircuitStudyRequest


class FaultCalculationService:
    """Application service for short-circuit and earth-fault calculations."""

    def calculate_short_circuit(
        self,
        payload: ShortCircuitStudyRequest,
    ) -> ShortCircuitStudyResult:
        """Calculate one validated short-circuit study."""

        if not isinstance(
            payload,
            ShortCircuitStudyRequest,
        ):
            raise TypeError("payload must be a ShortCircuitStudyRequest")

        return calculate_domain_short_circuit(payload.to_domain())


__all__ = [
    "FaultCalculationService",
]
