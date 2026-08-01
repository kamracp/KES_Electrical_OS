"""
Result models for HT panel engineering.
KESE-S2-M9
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.sources.ht_panel_models import (
    HTFeederType,
    HTPanelConstruction,
    HTPanelInstallation,
    HTRelayFunction,
    HTSwitchingDevice,
    HTSystemVoltage,
)


class HTPanelSizingStatus(StrEnum):
    """HT panel engineering result status."""

    VALID = "VALID"
    WARNING = "WARNING"
    NO_SOLUTION = "NO_SOLUTION"


class HTPanelWarningCode(StrEnum):
    """Structured HT panel warning codes."""

    HIGH_BUSBAR_LOADING = "HIGH_BUSBAR_LOADING"
    LOW_BUSBAR_LOADING = "LOW_BUSBAR_LOADING"
    BREAKING_CAPACITY_MARGIN_LOW = (
        "BREAKING_CAPACITY_MARGIN_LOW"
    )
    SHORT_TIME_WITHSTAND_MARGIN_LOW = (
        "SHORT_TIME_WITHSTAND_MARGIN_LOW"
    )
    CT_RATIO_MARGIN_LOW = "CT_RATIO_MARGIN_LOW"
    ARC_CLASSIFICATION_REQUIRED = (
        "ARC_CLASSIFICATION_REQUIRED"
    )
    REMOTE_OPERATION_RECOMMENDED = (
        "REMOTE_OPERATION_RECOMMENDED"
    )


def _normalize_required_text(
    field_name: str,
    value: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} must not be empty"
        )

    return normalized


@dataclass(frozen=True, slots=True)
class HTPanelWarning:
    """Structured HT panel engineering warning."""

    code: HTPanelWarningCode
    message: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.code,
            HTPanelWarningCode,
        ):
            raise TypeError(
                "code must be an HTPanelWarningCode value"
            )

        object.__setattr__(
            self,
            "message",
            _normalize_required_text(
                "message",
                self.message,
            ),
        )


@dataclass(frozen=True, slots=True)
class HTFeederResult:
    """Calculated HT feeder engineering result."""

    code: str
    name: str

    feeder_type: HTFeederType
    switching_device: HTSwitchingDevice

    design_current_a: Decimal
    rated_normal_current_a: Decimal
    current_loading_percent: Decimal

    prospective_short_circuit_current_ka: Decimal
    rated_short_circuit_breaking_current_ka: Decimal
    breaking_capacity_margin_ka: Decimal

    rated_short_time_withstand_current_ka: Decimal
    short_time_withstand_margin_ka: Decimal
    short_time_withstand_duration_s: Decimal

    rated_peak_withstand_current_ka: Decimal

    ct_primary_current_a: Decimal
    ct_secondary_current_a: Decimal
    ct_ratio: str
    ct_margin_a: Decimal

    relay_functions: tuple[HTRelayFunction, ...]

    warnings: tuple[HTPanelWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            _normalize_required_text(
                "code",
                self.code,
            ),
        )
        object.__setattr__(
            self,
            "name",
            _normalize_required_text(
                "name",
                self.name,
            ),
        )
        object.__setattr__(
            self,
            "ct_ratio",
            _normalize_required_text(
                "ct_ratio",
                self.ct_ratio,
            ),
        )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        if not all(
            isinstance(warning, HTPanelWarning)
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only HTPanelWarning records"
            )


@dataclass(frozen=True, slots=True)
class HTPanelSizingResult:
    """Immutable HT panel engineering result."""

    code: str
    name: str

    system_voltage: HTSystemVoltage
    installation: HTPanelInstallation
    construction: HTPanelConstruction

    total_feeders: int
    active_feeders: int
    spare_feeders: int

    bus_sections: int
    bus_couplers: int

    maximum_feeder_current_a: Decimal
    aggregate_design_current_a: Decimal

    busbar_rated_current_a: Decimal
    busbar_loading_percent: Decimal
    busbar_spare_capacity_a: Decimal

    maximum_fault_current_ka: Decimal
    busbar_short_time_withstand_current_ka: Decimal
    busbar_fault_margin_ka: Decimal

    busbar_peak_withstand_current_ka: Decimal

    feeder_results: tuple[HTFeederResult, ...]

    status: HTPanelSizingStatus
    warnings: tuple[HTPanelWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            _normalize_required_text(
                "code",
                self.code,
            ),
        )
        object.__setattr__(
            self,
            "name",
            _normalize_required_text(
                "name",
                self.name,
            ),
        )

        if self.total_feeders != (
            self.active_feeders
            + self.spare_feeders
        ):
            raise ValueError(
                "total_feeders must equal active_feeders "
                "plus spare_feeders"
            )

        if not isinstance(
            self.feeder_results,
            tuple,
        ):
            raise TypeError(
                "feeder_results must be a tuple"
            )

        if not all(
            isinstance(result, HTFeederResult)
            for result in self.feeder_results
        ):
            raise TypeError(
                "feeder_results must contain only "
                "HTFeederResult records"
            )

        if len(self.feeder_results) != self.total_feeders:
            raise ValueError(
                "feeder_results count must equal total_feeders"
            )

        if not isinstance(
            self.status,
            HTPanelSizingStatus,
        ):
            raise TypeError(
                "status must be an HTPanelSizingStatus value"
            )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        if not all(
            isinstance(warning, HTPanelWarning)
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only HTPanelWarning records"
            )

        warning_codes = tuple(
            warning.code
            for warning in self.warnings
        )

        if len(warning_codes) != len(set(warning_codes)):
            raise ValueError(
                "panel warning codes must be unique"
            )


__all__ = [
    "HTFeederResult",
    "HTPanelSizingResult",
    "HTPanelSizingStatus",
    "HTPanelWarning",
    "HTPanelWarningCode",
]
