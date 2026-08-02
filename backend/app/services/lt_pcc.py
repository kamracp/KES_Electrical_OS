"""
Service layer for LT PCC / Main Panel engineering.
KESE-S2-M10
"""

from app.domain.electrical.distribution.lt_pcc_engine import (
    calculate_lt_pcc_sizing as calculate_domain_lt_pcc_sizing,
)
from app.domain.electrical.distribution.lt_pcc_results import (
    LTPCCSizingResult,
)
from app.schemas.lt_pcc import (
    LTPCCSizingRequest,
)


class LTPCCService:
    """Application service for LT PCC engineering."""

    def calculate_lt_pcc_sizing(
        self,
        payload: LTPCCSizingRequest,
    ) -> LTPCCSizingResult:
        """Calculate one validated LT PCC arrangement."""

        if not isinstance(
            payload,
            LTPCCSizingRequest,
        ):
            raise TypeError(
                "payload must be an LTPCCSizingRequest"
            )

        return calculate_domain_lt_pcc_sizing(
            payload.to_domain()
        )


__all__ = [
    "LTPCCService",
]
