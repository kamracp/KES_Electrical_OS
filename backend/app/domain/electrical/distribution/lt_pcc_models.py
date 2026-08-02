"""
Domain input models for LT PCC / Main Panel engineering.
KESE-S2-M10
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.sources.common import (
    normalize_optional_text,
    normalize_required_text,
    require_positive_decimal,
)


class LTSystemVoltage(StrEnum):
    """Supported LT system voltages."""

    V_400 = "400_V"
    V_415 = "415_V"
    V_433 = "433_V"
    V_480 = "480_V"
    V_690 = "690_V"


class LTPanelInstallation(StrEnum):
    """LT panel installation environment."""

    INDOOR = "INDOOR"
    OUTDOOR = "OUTDOOR"


class LTPanelFormOfSeparation(StrEnum):
    """IEC 61439 form of internal separation."""

    FORM_1 = "FORM_1"
    FORM_2A = "FORM_2A"
    FORM_2B = "FORM_2B"
    FORM_3A = "FORM_3A"
    FORM_3B = "FORM_3B"
    FORM_4A = "FORM_4A"
    FORM_4B = "FORM_4B"


class LTFeederType(StrEnum):
    """LT feeder functional classification."""

    TRANSFORMER_INCOMER = "TRANSFORMER_INCOMER"
    DG_INCOMER = "DG_INCOMER"
    PV_INCOMER = "PV_INCOMER"
    UPS_INCOMER = "UPS_INCOMER"
    BUS_COUPLER = "BUS_COUPLER"
    BUS_SECTION = "BUS_SECTION"
    OUTGOING_FEEDER = "OUTGOING_FEEDER"
    MOTOR_FEEDER = "MOTOR_FEEDER"
    APFC_FEEDER = "APFC_FEEDER"
    ESSENTIAL_FEEDER = "ESSENTIAL_FEEDER"
    SPARE_FEEDER = "SPARE_FEEDER"


class LTSwitchingDevice(StrEnum):
    """LT switching and protection device type."""

    ACB = "ACB"
    MCCB = "MCCB"
    MCB = "MCB"
    SWITCH_DISCONNECTOR = "SWITCH_DISCONNECTOR"
    FUSE_SWITCH = "FUSE_SWITCH"


class LTTripUnitType(StrEnum):
    """LT breaker trip-unit classification."""

    THERMAL_MAGNETIC = "THERMAL_MAGNETIC"
    ELECTRONIC_LSI = "ELECTRONIC_LSI"
    ELECTRONIC_LSIG = "ELECTRONIC_LSIG"
    NONE = "NONE"


def _require_positive_integer(
    field_name: str,
    value: int,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"{field_name} must be an integer"
        )

    if value <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero"
        )


def _require_non_negative_integer(
    field_name: str,
    value: int,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"{field_name} must be an integer"
        )

    if value < 0:
        raise ValueError(
            f"{field_name} must not be negative"
        )


@dataclass(frozen=True, slots=True)
class LTFeederInput:
    """Immutable LT feeder engineering input."""

    code: str
    name: str

    feeder_type: LTFeederType
    switching_device: LTSwitchingDevice
    trip_unit_type: LTTripUnitType

    design_current_a: Decimal
    rated_current_a: Decimal

    prospective_short_circuit_current_ka: Decimal
    rated_ultimate_breaking_capacity_ka: Decimal
    rated_service_breaking_capacity_ka: Decimal
    rated_short_time_withstand_current_ka: Decimal

    number_of_poles: int = 4
    cable_count: int = 1
    spare_feeder: bool = False
    notes: str | None = None

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
        object.__setattr__(
            self,
            "notes",
            normalize_optional_text(
                "notes",
                self.notes,
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
                "trip_unit_type must be an LTTripUnitType value"
            )

        for field_name, value in {
            "design_current_a": self.design_current_a,
            "rated_current_a": self.rated_current_a,
            "prospective_short_circuit_current_ka": (
                self.prospective_short_circuit_current_ka
            ),
            "rated_ultimate_breaking_capacity_ka": (
                self.rated_ultimate_breaking_capacity_ka
            ),
            "rated_service_breaking_capacity_ka": (
                self.rated_service_breaking_capacity_ka
            ),
            "rated_short_time_withstand_current_ka": (
                self.rated_short_time_withstand_current_ka
            ),
        }.items():
            require_positive_decimal(
                field_name,
                value,
            )

        if self.rated_current_a < self.design_current_a:
            raise ValueError(
                "rated_current_a must not be below "
                "design_current_a"
            )

        if (
            self.rated_ultimate_breaking_capacity_ka
            < self.prospective_short_circuit_current_ka
        ):
            raise ValueError(
                "rated ultimate breaking capacity must not be "
                "below prospective short-circuit current"
            )

        if (
            self.rated_service_breaking_capacity_ka
            > self.rated_ultimate_breaking_capacity_ka
        ):
            raise ValueError(
                "rated service breaking capacity must not exceed "
                "rated ultimate breaking capacity"
            )

        if (
            self.rated_short_time_withstand_current_ka
            < self.prospective_short_circuit_current_ka
        ):
            raise ValueError(
                "rated short-time withstand current must not be "
                "below prospective short-circuit current"
            )

        if self.number_of_poles not in {2, 3, 4}:
            raise ValueError(
                "number_of_poles must be 2, 3 or 4"
            )

        _require_positive_integer(
            "cable_count",
            self.cable_count,
        )

        if not isinstance(self.spare_feeder, bool):
            raise TypeError(
                "spare_feeder must be a boolean"
            )


@dataclass(frozen=True, slots=True)
class LTPCCSizingInput:
    """Immutable LT PCC / Main Panel engineering input."""

    code: str
    name: str

    system_voltage: LTSystemVoltage
    frequency_hz: Decimal

    installation: LTPanelInstallation
    form_of_separation: LTPanelFormOfSeparation

    busbar_rated_current_a: Decimal
    busbar_short_time_withstand_current_ka: Decimal
    busbar_peak_withstand_current_ka: Decimal

    neutral_bus_rating_percent: Decimal
    earth_bus_rating_percent: Decimal

    feeders: tuple[LTFeederInput, ...]

    bus_sections: int = 1
    bus_couplers: int = 0
    spare_feeders: int = 0

    ip_rating: str = "IP42"

    apfc_required: bool = False
    metering_required: bool = True
    remote_operation_required: bool = False

    notes: str | None = None

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
        object.__setattr__(
            self,
            "ip_rating",
            normalize_required_text(
                "ip_rating",
                self.ip_rating,
            ),
        )
        object.__setattr__(
            self,
            "notes",
            normalize_optional_text(
                "notes",
                self.notes,
            ),
        )

        if not isinstance(
            self.system_voltage,
            LTSystemVoltage,
        ):
            raise TypeError(
                "system_voltage must be an LTSystemVoltage value"
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
            "frequency_hz": self.frequency_hz,
            "busbar_rated_current_a": (
                self.busbar_rated_current_a
            ),
            "busbar_short_time_withstand_current_ka": (
                self.busbar_short_time_withstand_current_ka
            ),
            "busbar_peak_withstand_current_ka": (
                self.busbar_peak_withstand_current_ka
            ),
            "neutral_bus_rating_percent": (
                self.neutral_bus_rating_percent
            ),
            "earth_bus_rating_percent": (
                self.earth_bus_rating_percent
            ),
        }.items():
            require_positive_decimal(
                field_name,
                value,
            )

        if not isinstance(self.feeders, tuple):
            raise TypeError(
                "feeders must be a tuple"
            )

        if not self.feeders:
            raise ValueError(
                "LT PCC must contain at least one feeder"
            )

        if not all(
            isinstance(
                feeder,
                LTFeederInput,
            )
            for feeder in self.feeders
        ):
            raise TypeError(
                "feeders must contain only LTFeederInput records"
            )

        feeder_codes = tuple(
            feeder.code
            for feeder in self.feeders
        )

        if len(feeder_codes) != len(set(feeder_codes)):
            raise ValueError(
                "LT feeder codes must be unique"
            )

        maximum_feeder_current = max(
            feeder.rated_current_a
            for feeder in self.feeders
        )

        if (
            self.busbar_rated_current_a
            < maximum_feeder_current
        ):
            raise ValueError(
                "busbar_rated_current_a must not be below "
                "the highest feeder rated current"
            )

        maximum_fault_current = max(
            feeder.prospective_short_circuit_current_ka
            for feeder in self.feeders
        )

        if (
            self.busbar_short_time_withstand_current_ka
            < maximum_fault_current
        ):
            raise ValueError(
                "busbar short-time withstand current must not "
                "be below the maximum feeder fault current"
            )

        _require_positive_integer(
            "bus_sections",
            self.bus_sections,
        )
        _require_non_negative_integer(
            "bus_couplers",
            self.bus_couplers,
        )
        _require_non_negative_integer(
            "spare_feeders",
            self.spare_feeders,
        )

        if self.bus_sections == 1 and self.bus_couplers != 0:
            raise ValueError(
                "single bus section cannot have a bus coupler"
            )

        if (
            self.bus_sections > 1
            and self.bus_couplers < 1
        ):
            raise ValueError(
                "multiple bus sections require at least "
                "one bus coupler"
            )

        for field_name, value in {
            "apfc_required": self.apfc_required,
            "metering_required": self.metering_required,
            "remote_operation_required": (
                self.remote_operation_required
            ),
        }.items():
            if not isinstance(value, bool):
                raise TypeError(
                    f"{field_name} must be a boolean"
                )


__all__ = [
    "LTFeederInput",
    "LTFeederType",
    "LTPanelFormOfSeparation",
    "LTPanelInstallation",
    "LTPCCSizingInput",
    "LTSystemVoltage",
    "LTSwitchingDevice",
    "LTTripUnitType",
]
