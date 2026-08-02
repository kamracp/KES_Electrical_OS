"""
Result models for LT PCC / Main Panel engineering.
KESE-S2-M10
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.distribution.lt_pcc_models import (
    LTFeederType,
    LTPanelFormOfSeparation,
    LTPanelInstallation,
    LTSystemVoltage,
    LTSwitchingDevice,
    LTTripUnitType,
)
from app.domain.electrical.sources.common import (
    normalize_required_text,
)


class LTPCCSizingStatus(StrEnum):
    """LT PCC engineering result status."""

    VALID = "VALID"
    WARNING = "WARNING"
    NO_SOLUTION = "NO_SOLUTION"


class LTPCCWarningCode(StrEnum):
    """Structured LT PCC warning codes."""

    HIGH_BUSBAR_LOADING = "HIGH_BUSBAR_LOADING"
    LOW_BUSBAR_LOADING = "LOW_BUSBAR_LOADING"
    ICU_MARGIN_LOW = "ICU_MARGIN_LOW"
    ICS_MARGIN_LOW = "ICS_MARGIN_LOW"
    ICW_MARGIN_LOW = "ICW_MARGIN_LOW"
    LOW_FEEDER_SPARE_CAPACITY = "LOW_FEEDER_SPARE_CAPACITY"
    APFC_REVIEW_REQUIRED = "APFC_REVIEW_REQUIRED"
    REMOTE_OPERATION_RECOMMENDED = (
        "REMOTE_OPERATION_RECOMMENDED"
    )


@dataclass(frozen=True, slots=True)
class LTPCCWarning:
    """Structured LT PCC engineering warning."""

    code: LTPCCWarningCode
    message: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.code,
            LTPCCWarningCode,
        ):
            raise TypeError(
                "code must be an LTPCCWarningCode value"
            )

        object.__setattr__(
            self,
            "message",
            normalize_required_text(
                "message",
                self.message,
            ),
        )


@dataclass(frozen=True, slots=True)
class LTFeederResult:
    """Calculated LT feeder engineering result."""

    code: str
    name: str

    feeder_type: LTFeederType
    switching_device: LTSwitchingDevice
    trip_unit_type: LTTripUnitType

    design_current_a: Decimal
    rated_current_a: Decimal
    loading_percent: Decimal
    spare_current_capacity_a: Decimal

    prospective_short_circuit_current_ka: Decimal

    rated_ultimate_breaking_capacity_ka: Decimal
    icu_margin_ka: Decimal

    rated_service_breaking_capacity_ka: Decimal
    ics_margin_ka: Decimal

    rated_short_time_withstand_current_ka: Decimal
    icw_margin_ka: Decimal

    number_of_poles: int
    cable_count: int
    spare_feeder: bool

    warnings: tuple[LTPCCWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            normalize_required_text(
                "code",
                self.code,
            ),
        )
        object.__setattr__(
            self,
            "name",
            normalize_required_text(
                "name",
                self.name,
            ),
        )

        if not isinstance(
            self.feeder_type,
            LTFeederType,
        ):
            raise TypeError(
                "feeder_type must be an LTFeederType value"
            )

        if not isinstance(
            self.switching_device,
            LTSwitchingDevice,
        ):
            raise TypeError(
                "switching_device must be an "
                "LTSwitchingDevice value"
            )

        if not isinstance(
            self.trip_unit_type,
            LTTripUnitType,
        ):
            raise TypeError(
                "trip_unit_type must be an "
                "LTTripUnitType value"
            )

        if not isinstance(
            self.number_of_poles,
            int,
        ) or isinstance(
            self.number_of_poles,
            bool,
        ):
            raise TypeError(
                "number_of_poles must be an integer"
            )

        if self.number_of_poles not in {2, 3, 4}:
            raise ValueError(
                "number_of_poles must be 2, 3 or 4"
            )

        if not isinstance(
            self.cable_count,
            int,
        ) or isinstance(
            self.cable_count,
            bool,
        ):
            raise TypeError(
                "cable_count must be an integer"
            )

        if self.cable_count <= 0:
            raise ValueError(
                "cable_count must be greater than zero"
            )

        if not isinstance(
            self.spare_feeder,
            bool,
        ):
            raise TypeError(
                "spare_feeder must be a boolean"
            )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        if not all(
            isinstance(
                warning,
                LTPCCWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only "
                "LTPCCWarning records"
            )

        warning_codes = tuple(
            warning.code
            for warning in self.warnings
        )

        if len(warning_codes) != len(
            set(warning_codes)
        ):
            raise ValueError(
                "feeder warning codes must be unique"
            )


@dataclass(frozen=True, slots=True)
class LTPCCSizingResult:
    """Immutable LT PCC / Main Panel engineering result."""

    code: str
    name: str

    system_voltage: LTSystemVoltage
    installation: LTPanelInstallation
    form_of_separation: LTPanelFormOfSeparation

    total_feeders: int
    active_feeders: int
    spare_feeders: int

    bus_sections: int
    bus_couplers: int

    aggregate_design_current_a: Decimal
    maximum_feeder_rated_current_a: Decimal

    busbar_rated_current_a: Decimal
    busbar_loading_percent: Decimal
    busbar_spare_capacity_a: Decimal

    maximum_fault_current_ka: Decimal
    busbar_short_time_withstand_current_ka: Decimal
    busbar_fault_margin_ka: Decimal

    busbar_peak_withstand_current_ka: Decimal

    neutral_bus_rating_percent: Decimal
    earth_bus_rating_percent: Decimal

    apfc_required: bool
    metering_required: bool
    remote_operation_required: bool

    feeder_results: tuple[LTFeederResult, ...]

    status: LTPCCSizingStatus
    warnings: tuple[LTPCCWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            normalize_required_text(
                "code",
                self.code,
            ),
        )
        object.__setattr__(
            self,
            "name",
            normalize_required_text(
                "name",
                self.name,
            ),
        )

        if not isinstance(
            self.system_voltage,
            LTSystemVoltage,
        ):
            raise TypeError(
                "system_voltage must be an "
                "LTSystemVoltage value"
            )

        if not isinstance(
            self.installation,
            LTPanelInstallation,
        ):
            raise TypeError(
                "installation must be an "
                "LTPanelInstallation value"
            )

        if not isinstance(
            self.form_of_separation,
            LTPanelFormOfSeparation,
        ):
            raise TypeError(
                "form_of_separation must be an "
                "LTPanelFormOfSeparation value"
            )

        for field_name, value in {
            "total_feeders": self.total_feeders,
            "active_feeders": self.active_feeders,
            "spare_feeders": self.spare_feeders,
            "bus_sections": self.bus_sections,
            "bus_couplers": self.bus_couplers,
        }.items():
            if isinstance(value, bool) or not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{field_name} must be an integer"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        if self.total_feeders != (
            self.active_feeders
            + self.spare_feeders
        ):
            raise ValueError(
                "total_feeders must equal active_feeders "
                "plus spare_feeders"
            )

        if self.bus_sections <= 0:
            raise ValueError(
                "bus_sections must be greater than zero"
            )

        if not isinstance(
            self.feeder_results,
            tuple,
        ):
            raise TypeError(
                "feeder_results must be a tuple"
            )

        if not all(
            isinstance(
                result,
                LTFeederResult,
            )
            for result in self.feeder_results
        ):
            raise TypeError(
                "feeder_results must contain only "
                "LTFeederResult records"
            )

        if len(
            self.feeder_results
        ) != self.total_feeders:
            raise ValueError(
                "feeder_results count must equal "
                "total_feeders"
            )

        if not isinstance(
            self.apfc_required,
            bool,
        ):
            raise TypeError(
                "apfc_required must be a boolean"
            )

        if not isinstance(
            self.metering_required,
            bool,
        ):
            raise TypeError(
                "metering_required must be a boolean"
            )

        if not isinstance(
            self.remote_operation_required,
            bool,
        ):
            raise TypeError(
                "remote_operation_required must be a boolean"
            )

        if not isinstance(
            self.status,
            LTPCCSizingStatus,
        ):
            raise TypeError(
                "status must be an LTPCCSizingStatus value"
            )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        if not all(
            isinstance(
                warning,
                LTPCCWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only "
                "LTPCCWarning records"
            )

        warning_codes = tuple(
            warning.code
            for warning in self.warnings
        )

        if len(warning_codes) != len(
            set(warning_codes)
        ):
            raise ValueError(
                "panel warning codes must be unique"
            )


__all__ = [
    "LTFeederResult",
    "LTPCCSizingResult",
    "LTPCCSizingStatus",
    "LTPCCWarning",
    "LTPCCWarningCode",
]
