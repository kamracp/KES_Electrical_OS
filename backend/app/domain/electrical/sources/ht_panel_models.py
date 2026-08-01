"""
Domain input models for HT panel engineering.
KESE-S2-M9
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.sources.common import (
    normalize_optional_text,
    normalize_required_text,
    require_decimal,
    require_positive_decimal,
)


class HTSystemVoltage(StrEnum):
    """Supported nominal HT system voltages."""

    KV_3_3 = "3.3_KV"
    KV_6_6 = "6.6_KV"
    KV_11 = "11_KV"
    KV_22 = "22_KV"
    KV_33 = "33_KV"


class HTPanelInstallation(StrEnum):
    """HT panel installation environment."""

    INDOOR = "INDOOR"
    OUTDOOR = "OUTDOOR"


class HTPanelConstruction(StrEnum):
    """HT switchgear construction type."""

    METAL_CLAD = "METAL_CLAD"
    METAL_ENCLOSED = "METAL_ENCLOSED"
    RMU = "RMU"


class HTFeederType(StrEnum):
    """HT feeder functional classification."""

    INCOMER = "INCOMER"
    TRANSFORMER_FEEDER = "TRANSFORMER_FEEDER"
    MOTOR_FEEDER = "MOTOR_FEEDER"
    BUS_COUPLER = "BUS_COUPLER"
    BUS_SECTION = "BUS_SECTION"
    OUTGOING_FEEDER = "OUTGOING_FEEDER"
    CAPACITOR_FEEDER = "CAPACITOR_FEEDER"
    DG_FEEDER = "DG_FEEDER"
    PV_FEEDER = "PV_FEEDER"


class HTSwitchingDevice(StrEnum):
    """Primary switching-device type."""

    VCB = "VCB"
    SF6_BREAKER = "SF6_BREAKER"
    LOAD_BREAK_SWITCH = "LOAD_BREAK_SWITCH"
    FUSE_SWITCH = "FUSE_SWITCH"
    DISCONNECTOR = "DISCONNECTOR"


class HTRelayFunction(StrEnum):
    """Supported protection relay functions."""

    OVERCURRENT = "50_51"
    EARTH_FAULT = "50N_51N"
    DIRECTIONAL_OVERCURRENT = "67"
    DIRECTIONAL_EARTH_FAULT = "67N"
    UNDER_VOLTAGE = "27"
    OVER_VOLTAGE = "59"
    UNDER_FREQUENCY = "81U"
    OVER_FREQUENCY = "81O"
    NEGATIVE_SEQUENCE = "46"
    THERMAL_OVERLOAD = "49"
    DIFFERENTIAL = "87"
    RESTRICTED_EARTH_FAULT = "64REF"
    BREAKER_FAILURE = "50BF"
    LOCKOUT = "86"


def _require_positive_integer(
    field_name: str,
    value: int,
) -> None:
    """Require a non-boolean integer greater than zero."""

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
    """Require a non-boolean integer equal to or above zero."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"{field_name} must be an integer"
        )

    if value < 0:
        raise ValueError(
            f"{field_name} must not be negative"
        )


@dataclass(frozen=True, slots=True)
class HTFeederInput:
    """Immutable HT feeder engineering input."""

    code: str
    name: str

    feeder_type: HTFeederType
    switching_device: HTSwitchingDevice

    design_current_a: Decimal
    prospective_short_circuit_current_ka: Decimal

    rated_normal_current_a: Decimal
    rated_short_circuit_breaking_current_ka: Decimal
    rated_short_time_withstand_current_ka: Decimal
    short_time_withstand_duration_s: Decimal
    rated_peak_withstand_current_ka: Decimal

    ct_primary_current_a: Decimal
    ct_secondary_current_a: Decimal = Decimal("1")
    ct_protection_class: str = "5P20"
    ct_metering_class: str = "0.5"

    relay_functions: tuple[HTRelayFunction, ...] = (
        HTRelayFunction.OVERCURRENT,
        HTRelayFunction.EARTH_FAULT,
    )

    cable_count: int = 1
    spare_feeder: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize HT feeder inputs."""

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
            "ct_protection_class",
            normalize_required_text(
                "ct_protection_class",
                self.ct_protection_class,
            ),
        )
        object.__setattr__(
            self,
            "ct_metering_class",
            normalize_required_text(
                "ct_metering_class",
                self.ct_metering_class,
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
            HTFeederType,
        ):
            raise TypeError(
                "feeder_type must be an HTFeederType value"
            )

        if not isinstance(
            self.switching_device,
            HTSwitchingDevice,
        ):
            raise TypeError(
                "switching_device must be an HTSwitchingDevice value"
            )

        for field_name, value in {
            "design_current_a": self.design_current_a,
            "prospective_short_circuit_current_ka": (
                self.prospective_short_circuit_current_ka
            ),
            "rated_normal_current_a": (
                self.rated_normal_current_a
            ),
            "rated_short_circuit_breaking_current_ka": (
                self.rated_short_circuit_breaking_current_ka
            ),
            "rated_short_time_withstand_current_ka": (
                self.rated_short_time_withstand_current_ka
            ),
            "short_time_withstand_duration_s": (
                self.short_time_withstand_duration_s
            ),
            "rated_peak_withstand_current_ka": (
                self.rated_peak_withstand_current_ka
            ),
            "ct_primary_current_a": self.ct_primary_current_a,
            "ct_secondary_current_a": self.ct_secondary_current_a,
        }.items():
            require_positive_decimal(
                field_name,
                value,
            )

        if (
            self.rated_normal_current_a
            < self.design_current_a
        ):
            raise ValueError(
                "rated_normal_current_a must not be below "
                "design_current_a"
            )

        if (
            self.rated_short_circuit_breaking_current_ka
            < self.prospective_short_circuit_current_ka
        ):
            raise ValueError(
                "rated short-circuit breaking current must not "
                "be below prospective short-circuit current"
            )

        if (
            self.rated_short_time_withstand_current_ka
            < self.prospective_short_circuit_current_ka
        ):
            raise ValueError(
                "rated short-time withstand current must not "
                "be below prospective short-circuit current"
            )

        if (
            self.rated_peak_withstand_current_ka
            < self.rated_short_time_withstand_current_ka
        ):
            raise ValueError(
                "rated_peak_withstand_current_ka must not be "
                "below rated_short_time_withstand_current_ka"
            )

        if self.ct_primary_current_a < self.design_current_a:
            raise ValueError(
                "ct_primary_current_a must not be below "
                "design_current_a"
            )

        if self.ct_secondary_current_a not in {
            Decimal("1"),
            Decimal("5"),
        }:
            raise ValueError(
                "ct_secondary_current_a must be 1 or 5"
            )

        if not isinstance(
            self.relay_functions,
            tuple,
        ):
            raise TypeError(
                "relay_functions must be a tuple"
            )

        if not self.relay_functions:
            raise ValueError(
                "at least one relay function is required"
            )

        if not all(
            isinstance(
                function,
                HTRelayFunction,
            )
            for function in self.relay_functions
        ):
            raise TypeError(
                "relay_functions must contain only "
                "HTRelayFunction values"
            )

        if len(self.relay_functions) != len(
            set(self.relay_functions)
        ):
            raise ValueError(
                "relay functions must be unique"
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
class HTPanelSizingInput:
    """Immutable HT panel engineering input."""

    code: str
    name: str

    system_voltage: HTSystemVoltage
    highest_system_voltage_kv: Decimal
    frequency_hz: Decimal

    installation: HTPanelInstallation
    construction: HTPanelConstruction

    busbar_rated_current_a: Decimal
    busbar_short_time_withstand_current_ka: Decimal
    busbar_short_time_duration_s: Decimal
    busbar_peak_withstand_current_ka: Decimal

    rated_insulation_level_kv: Decimal
    lightning_impulse_withstand_voltage_kvp: Decimal

    feeders: tuple[HTFeederInput, ...]

    bus_sections: int = 1
    bus_couplers: int = 0
    spare_feeders: int = 0

    indoor_ip_rating: str = "IP4X"
    outdoor_ip_rating: str = "IP54"

    earthing_switch_required: bool = True
    arc_classification_required: bool = True
    remote_operation_required: bool = False

    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize HT panel inputs."""

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
            "indoor_ip_rating",
            normalize_required_text(
                "indoor_ip_rating",
                self.indoor_ip_rating,
            ),
        )
        object.__setattr__(
            self,
            "outdoor_ip_rating",
            normalize_required_text(
                "outdoor_ip_rating",
                self.outdoor_ip_rating,
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
            HTSystemVoltage,
        ):
            raise TypeError(
                "system_voltage must be an HTSystemVoltage value"
            )

        if not isinstance(
            self.installation,
            HTPanelInstallation,
        ):
            raise TypeError(
                "installation must be an HTPanelInstallation value"
            )

        if not isinstance(
            self.construction,
            HTPanelConstruction,
        ):
            raise TypeError(
                "construction must be an HTPanelConstruction value"
            )

        for field_name, value in {
            "highest_system_voltage_kv": (
                self.highest_system_voltage_kv
            ),
            "frequency_hz": self.frequency_hz,
            "busbar_rated_current_a": (
                self.busbar_rated_current_a
            ),
            "busbar_short_time_withstand_current_ka": (
                self.busbar_short_time_withstand_current_ka
            ),
            "busbar_short_time_duration_s": (
                self.busbar_short_time_duration_s
            ),
            "busbar_peak_withstand_current_ka": (
                self.busbar_peak_withstand_current_ka
            ),
            "rated_insulation_level_kv": (
                self.rated_insulation_level_kv
            ),
            "lightning_impulse_withstand_voltage_kvp": (
                self.lightning_impulse_withstand_voltage_kvp
            ),
        }.items():
            require_positive_decimal(
                field_name,
                value,
            )

        if (
            self.busbar_peak_withstand_current_ka
            < self.busbar_short_time_withstand_current_ka
        ):
            raise ValueError(
                "busbar peak withstand current must not be below "
                "busbar short-time withstand current"
            )

        if not isinstance(self.feeders, tuple):
            raise TypeError(
                "feeders must be a tuple"
            )

        if not self.feeders:
            raise ValueError(
                "HT panel must contain at least one feeder"
            )

        if not all(
            isinstance(
                feeder,
                HTFeederInput,
            )
            for feeder in self.feeders
        ):
            raise TypeError(
                "feeders must contain only HTFeederInput records"
            )

        feeder_codes = tuple(
            feeder.code
            for feeder in self.feeders
        )

        if len(feeder_codes) != len(set(feeder_codes)):
            raise ValueError(
                "HT feeder codes must be unique"
            )

        maximum_feeder_current = max(
            feeder.rated_normal_current_a
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
            "earthing_switch_required": (
                self.earthing_switch_required
            ),
            "arc_classification_required": (
                self.arc_classification_required
            ),
            "remote_operation_required": (
                self.remote_operation_required
            ),
        }.items():
            if not isinstance(value, bool):
                raise TypeError(
                    f"{field_name} must be a boolean"
                )


__all__ = [
    "HTFeederInput",
    "HTFeederType",
    "HTPanelConstruction",
    "HTPanelInstallation",
    "HTPanelSizingInput",
    "HTRelayFunction",
    "HTSwitchingDevice",
    "HTSystemVoltage",
]
