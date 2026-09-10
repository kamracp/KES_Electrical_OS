"""
Service layer for cable sizing and ampacity engineering calculations.
KESE-S2-M13
"""

from app.domain.electrical.cable.cable_engine import (
    CableSizingEngine,
)
from app.domain.electrical.cable.cable_results import (
    CableSizingResult,
)
from app.schemas.cable import (
    CableSizingRequest,
)


class CableSizingService:
    """
    Application service for cable sizing and ampacity engineering.

    Converts validated API request schemas to immutable domain records,
    executes pure domain cable sizing and voltage drop calculation logic,
    and returns domain calculation results.
    """

    def calculate_cable_sizing(
        self,
        payload: CableSizingRequest,
    ) -> CableSizingResult:
        """Calculate one validated cable sizing study."""

        if not isinstance(payload, CableSizingRequest):
            raise TypeError("payload must be a CableSizingRequest")

        return CableSizingEngine.calculate(payload.to_domain())


__all__ = [
    "CableSizingService",
]
