"""
Domain result models for UPS source sizing.

Mission: KESE-S2-M7
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.sources.ups_models import (
    UPSBatteryTechnology,
    UPSPhaseConfiguration,
    UPSRedundancyMode,
    UPSTopology,
)


class UPSSizingStatus(StrEnum):
    """UPS sizing outcome classification."""

    SELECTED = "SELECTED"
    NO_STANDARD_RATING_AVAILABLE = "NO_STANDARD_RATING_AVAILABLE"


@dataclass(frozen=True, slots=True)
class UPSSizingResult:
    """Immutable UPS source-sizing calculation result."""

    code: str
    name: str

    critical_load_kw: Decimal
    base_load_kva: Decimal
    design_load_kva: Decimal
    derated_required_capacity_kva: Decimal

    required_capacity_per_duty_module_kva: Decimal
    selected_unit_rating_kva: Decimal | None

    duty_modules: int
    redundant_modules: int
    total_installed_modules: int

    duty_capacity_kva: Decimal | None
    total_installed_capacity_kva: Decimal | None
    spare_capacity_kva: Decimal | None
    loading_percent: Decimal | None

    required_runtime_minutes: Decimal
    estimated_output_energy_kwh: Decimal
    estimated_dc_energy_kwh: Decimal

    topology: UPSTopology
    phase_configuration: UPSPhaseConfiguration
    redundancy_mode: UPSRedundancyMode
    battery_technology: UPSBatteryTechnology

    status: UPSSizingStatus
    notes: str | None = None


__all__ = [
    "UPSSizingResult",
    "UPSSizingStatus",
]
