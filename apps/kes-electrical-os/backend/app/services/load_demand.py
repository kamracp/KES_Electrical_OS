"""
Service layer for electrical load and demand calculations.
KESE-S2-M2
"""

from kes_electrical_core.loads.engine import (
    calculate_load as calculate_domain_load,
)
from kes_electrical_core.loads.engine import (
    calculate_load_group as calculate_domain_load_group,
)
from kes_electrical_core.loads.results import (
    LoadCalculationResult,
    LoadGroupCalculationResult,
)
from app.schemas.load_demand import (
    LoadCalculationRequest,
    LoadGroupCalculationRequest,
)


class LoadDemandService:
    """
    Application service for load and demand calculations.

    The service converts validated API schemas into immutable domain
    records and delegates all engineering calculations to the pure
    domain engine.
    """

    def calculate_load(
        self,
        payload: LoadCalculationRequest,
    ) -> LoadCalculationResult:
        """Calculate one validated electrical load."""

        if not isinstance(payload, LoadCalculationRequest):
            raise TypeError(
                "payload must be a LoadCalculationRequest"
            )

        return calculate_domain_load(
            payload.to_domain()
        )

    def calculate_load_group(
        self,
        payload: LoadGroupCalculationRequest,
    ) -> LoadGroupCalculationResult:
        """Calculate one validated electrical load group."""

        if not isinstance(
            payload,
            LoadGroupCalculationRequest,
        ):
            raise TypeError(
                "payload must be a LoadGroupCalculationRequest"
            )

        return calculate_domain_load_group(
            payload.to_domain()
        )


__all__ = [
    "LoadDemandService",
]