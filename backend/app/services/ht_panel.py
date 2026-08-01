"""
Service layer for HT panel engineering.
KESE-S2-M9
"""

from app.domain.electrical.sources.ht_panel_engine import (
    calculate_ht_panel_sizing as calculate_domain_ht_panel_sizing,
)
from app.domain.electrical.sources.ht_panel_results import (
    HTPanelSizingResult,
)
from app.schemas.ht_panel import (
    HTPanelSizingRequest,
)


class HTPanelService:
    """Application service for HT panel engineering."""

    def calculate_ht_panel_sizing(
        self,
        payload: HTPanelSizingRequest,
    ) -> HTPanelSizingResult:
        """Calculate one validated HT panel arrangement."""

        if not isinstance(
            payload,
            HTPanelSizingRequest,
        ):
            raise TypeError(
                "payload must be an HTPanelSizingRequest"
            )

        return calculate_domain_ht_panel_sizing(
            payload.to_domain()
        )


__all__ = [
    "HTPanelService",
]
