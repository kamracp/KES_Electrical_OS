"""
Domain input models for intelligent switchgear selection.
KESE-S2-M11
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.sources.common import (
    normalize_optional_text,
    normalize_required_text,
    require_non_negative_decimal,
    require_positive_decimal,
    require_ratio,
)


class SwitchgearDeviceType(StrEnum):
    """Supported LV switching and protection devices."""

    ACB = "ACB"
    MCCB = "MCCB"
    MCB = "MCB"
    MPCB = "MPCB"
    FUSE_SWITCH = "FUSE_SWITCH"
    SWITCH_DISCONNECTOR = "SWITCH_DISCONNECTOR"


class SwitchgearApplication(StrEnum):
    """Switchgear application duty."""

    INCOMER = "INCOMER"
    BUS_COUPLER = "BUS_COUPLER"
    OUTGOING_FEEDER = "OUTGOING_FEEDER"
    MOTOR_FEEDER = "MOTOR_FEEDER"
    TRANSFORMER_FEEDER = "TRANSFORMER_FEEDER"
    GENERATOR_FEEDER = "GENERATOR_FEEDER"
    UPS_FEEDER = "UPS_FEEDER"
    PV_FEEDER = "PV_FEEDER"
    CAPACITOR_FEEDER = "CAPACITOR_FEEDER"


class SwitchgearTripUnitType(StrEnum):
    """Protection trip-unit classification."""

    NONE = "NONE"
    THERMAL_MAGNETIC = "THERMAL_MAGNETIC"
    ELECTRONIC_LI = "ELECTRONIC_LI"
    ELECTRONIC_LSI = "ELECTRONIC_LSI"
    ELECTRONIC_LSIG = "ELECTRONIC_LSIG"


class CoordinationType(StrEnum):
    """Required protection coordination objective."""

    NONE = "NONE"
    SELECTIVITY = "SELECTIVITY"
    CASCADING = "CASCADING"
    TYPE_1 = "TYPE_1"
    TYPE_2 = "TYPE_2"


class ManufacturerSource(StrEnum):
    """Design-resource source classification."""

    MANUFACTURER_NEUTRAL = "MANUFACTURER_NEUTRAL"
    SCHNEIDER_ELECTRIC = "SCHNEIDER_ELECTRIC"
    SIEMENS = "SIEMENS"
    ABB = "ABB"
    L_AND_T = "L_AND_T"


@dataclass(frozen=True, slots=True)
class ProtectionSettingsInput:
    """Protection settings for an adjustable trip unit."""

    long_time_pickup_a: Decimal | None = None
    long_time_delay_s: Decimal | None = None

    short_time_pickup_a: Decimal | None = None
    short_time_delay_s: Decimal | None = None

    instantaneous_pickup_a: Decimal | None = None

    ground_fault_pickup_a: Decimal | None = None
    ground_fault_delay_s: Decimal | None = None

    def __post_init__(self) -> None:
        optional_positive_values = {
            "long_time_pickup_a": self.long_time_pickup_a,
            "long_time_delay_s": self.long_time_delay_s,
            "short_time_pickup_a": self.short_time_pickup_a,
            "short_time_delay_s": self.short_time_delay_s,
            "instantaneous_pickup_a": self.instantaneous_pickup_a,
            "ground_fault_pickup_a": self.ground_fault_pickup_a,
            "ground_fault_delay_s": self.ground_fault_delay_s,
        }

        for field_name, value in optional_positive_values.items():
            if value is not None:
                require_positive_decimal(field_name, value)


@dataclass(frozen=True, slots=True)
class SwitchgearCandidate:
    """One manufacturer-neutral or manufacturer-specific device candidate."""

    code: str
    family: str

    manufacturer: ManufacturerSource
    device_type: SwitchgearDeviceType
    trip_unit_type: SwitchgearTripUnitType

    frame_current_a: Decimal
    rated_current_a: Decimal

    rated_operational_voltage_v: Decimal

    ultimate_breaking_capacity_ka: Decimal
    service_breaking_capacity_ka: Decimal
    short_time_withstand_current_ka: Decimal

    service_breaking_ratio: Decimal

    number_of_poles: int
    withdrawable: bool = False
    communication_capable: bool = False

    reference_document: str | None = None
    reference_revision: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            normalize_required_text("code", self.code),
        )
        object.__setattr__(
            self,
            "family",
            normalize_required_text("family", self.family),
        )
        object.__setattr__(
            self,
            "reference_document",
            normalize_optional_text(
                "reference_document",
                self.reference_document,
            ),
        )
        object.__setattr__(
            self,
            "reference_revision",
            normalize_optional_text(
                "reference_revision",
                self.reference_revision,
            ),
        )
        object.__setattr__(
            self,
            "notes",
            normalize_optional_text("notes", self.notes),
        )

        if not isinstance(self.manufacturer, ManufacturerSource):
            raise TypeError(
                "manufacturer must be a ManufacturerSource value"
            )

        if not isinstance(self.device_type, SwitchgearDeviceType):
            raise TypeError(
                "device_type must be a SwitchgearDeviceType value"
            )

        if not isinstance(self.trip_unit_type, SwitchgearTripUnitType):
            raise TypeError(
                "trip_unit_type must be a SwitchgearTripUnitType value"
            )

        for field_name, value in {
            "frame_current_a": self.frame_current_a,
            "rated_current_a": self.rated_current_a,
            "rated_operational_voltage_v": (
                self.rated_operational_voltage_v
            ),
            "ultimate_breaking_capacity_ka": (
                self.ultimate_breaking_capacity_ka
            ),
            "service_breaking_capacity_ka": (
                self.service_breaking_capacity_ka
            ),
            "short_time_withstand_current_ka": (
                self.short_time_withstand_current_ka
            ),
        }.items():
            require_positive_decimal(field_name, value)

        require_ratio(
            "service_breaking_ratio",
            self.service_breaking_ratio,
        )

        if self.rated_current_a > self.frame_current_a:
            raise ValueError(
                "rated_current_a must not exceed frame_current_a"
            )

        if (
            self.service_breaking_capacity_ka
            > self.ultimate_breaking_capacity_ka
        ):
            raise ValueError(
                "service breaking capacity must not exceed "
                "ultimate breaking capacity"
            )

        calculated_ratio = (
            self.service_breaking_capacity_ka
            / self.ultimate_breaking_capacity_ka
        )

        if calculated_ratio != self.service_breaking_ratio:
            raise ValueError(
                "service_breaking_ratio must equal Ics divided by Icu"
            )

        if self.number_of_poles not in {1, 2, 3, 4}:
            raise ValueError(
                "number_of_poles must be 1, 2, 3 or 4"
            )

        if not isinstance(self.withdrawable, bool):
            raise TypeError("withdrawable must be a boolean")

        if not isinstance(self.communication_capable, bool):
            raise TypeError(
                "communication_capable must be a boolean"
            )


@dataclass(frozen=True, slots=True)
class SwitchgearSelectionInput:
    """Immutable switchgear-selection engineering input."""

    code: str
    name: str

    application: SwitchgearApplication
    required_device_type: SwitchgearDeviceType

    system_voltage_v: Decimal
    design_current_a: Decimal
    prospective_short_circuit_current_ka: Decimal

    minimum_service_breaking_ratio: Decimal = Decimal("1")
    minimum_short_time_withstand_current_ka: Decimal = Decimal("0")

    number_of_poles: int = 4

    coordination_type: CoordinationType = CoordinationType.NONE

    upstream_device_code: str | None = None
    downstream_device_code: str | None = None

    protection_settings: ProtectionSettingsInput | None = None

    candidates: tuple[SwitchgearCandidate, ...] = ()

    cpwd_reference: str | None = None
    standard_reference: str | None = None
    manufacturer_reference_required: bool = False

    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            normalize_required_text("code", self.code),
        )
        object.__setattr__(
            self,
            "name",
            normalize_required_text("name", self.name),
        )
        object.__setattr__(
            self,
            "upstream_device_code",
            normalize_optional_text(
                "upstream_device_code",
                self.upstream_device_code,
            ),
        )
        object.__setattr__(
            self,
            "downstream_device_code",
            normalize_optional_text(
                "downstream_device_code",
                self.downstream_device_code,
            ),
        )
        object.__setattr__(
            self,
            "cpwd_reference",
            normalize_optional_text(
                "cpwd_reference",
                self.cpwd_reference,
            ),
        )
        object.__setattr__(
            self,
            "standard_reference",
            normalize_optional_text(
                "standard_reference",
                self.standard_reference,
            ),
        )
        object.__setattr__(
            self,
            "notes",
            normalize_optional_text("notes", self.notes),
        )

        if not isinstance(
            self.application,
            SwitchgearApplication,
        ):
            raise TypeError(
                "application must be a SwitchgearApplication value"
            )

        if not isinstance(
            self.required_device_type,
            SwitchgearDeviceType,
        ):
            raise TypeError(
                "required_device_type must be a "
                "SwitchgearDeviceType value"
            )

        if not isinstance(
            self.coordination_type,
            CoordinationType,
        ):
            raise TypeError(
                "coordination_type must be a CoordinationType value"
            )

        require_positive_decimal(
            "system_voltage_v",
            self.system_voltage_v,
        )
        require_positive_decimal(
            "design_current_a",
            self.design_current_a,
        )
        require_positive_decimal(
            "prospective_short_circuit_current_ka",
            self.prospective_short_circuit_current_ka,
        )
        require_ratio(
            "minimum_service_breaking_ratio",
            self.minimum_service_breaking_ratio,
        )
        require_non_negative_decimal(
            "minimum_short_time_withstand_current_ka",
            self.minimum_short_time_withstand_current_ka,
        )

        if self.number_of_poles not in {1, 2, 3, 4}:
            raise ValueError(
                "number_of_poles must be 1, 2, 3 or 4"
            )

        if self.protection_settings is not None and not isinstance(
            self.protection_settings,
            ProtectionSettingsInput,
        ):
            raise TypeError(
                "protection_settings must be a "
                "ProtectionSettingsInput record or None"
            )

        if not isinstance(self.candidates, tuple):
            raise TypeError("candidates must be a tuple")

        if not self.candidates:
            raise ValueError(
                "at least one switchgear candidate is required"
            )

        if not all(
            isinstance(candidate, SwitchgearCandidate)
            for candidate in self.candidates
        ):
            raise TypeError(
                "candidates must contain only "
                "SwitchgearCandidate records"
            )

        candidate_codes = tuple(
            candidate.code
            for candidate in self.candidates
        )

        if len(candidate_codes) != len(set(candidate_codes)):
            raise ValueError(
                "switchgear candidate codes must be unique"
            )

        if not isinstance(
            self.manufacturer_reference_required,
            bool,
        ):
            raise TypeError(
                "manufacturer_reference_required must be a boolean"
            )

        if (
            self.coordination_type is not CoordinationType.NONE
            and self.upstream_device_code is None
            and self.downstream_device_code is None
        ):
            raise ValueError(
                "coordination selection requires an upstream "
                "or downstream device reference"
            )


__all__ = [
    "CoordinationType",
    "ManufacturerSource",
    "ProtectionSettingsInput",
    "SwitchgearApplication",
    "SwitchgearCandidate",
    "SwitchgearDeviceType",
    "SwitchgearSelectionInput",
    "SwitchgearTripUnitType",
]
