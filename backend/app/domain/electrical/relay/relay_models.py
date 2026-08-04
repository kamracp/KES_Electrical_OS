"""
Domain models for protection relays and TCC engineering.
KESE-S2-M12
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.sources.common import (
    normalize_optional_text,
    normalize_required_text,
    require_non_negative_decimal,
    require_positive_decimal,
)


class RelayFunction(StrEnum):
    """Supported ANSI protection functions."""

    PHASE_OVERCURRENT = "50_51"
    EARTH_FAULT = "50N_51N"
    DIRECTIONAL_OVERCURRENT = "67"
    DIRECTIONAL_EARTH_FAULT = "67N"
    THERMAL_OVERLOAD = "49"
    UNDER_VOLTAGE = "27"
    OVER_VOLTAGE = "59"
    NEGATIVE_SEQUENCE = "46"
    DIFFERENTIAL = "87"
    RESTRICTED_EARTH_FAULT = "64REF"
    BREAKER_FAILURE = "50BF"


class RelayCurveFamily(StrEnum):
    """Supported relay time-current curve families."""

    IEC_STANDARD_INVERSE = "IEC_STANDARD_INVERSE"
    IEC_VERY_INVERSE = "IEC_VERY_INVERSE"
    IEC_EXTREMELY_INVERSE = "IEC_EXTREMELY_INVERSE"
    IEC_LONG_TIME_INVERSE = "IEC_LONG_TIME_INVERSE"
    IEEE_MODERATELY_INVERSE = "IEEE_MODERATELY_INVERSE"
    IEEE_VERY_INVERSE = "IEEE_VERY_INVERSE"
    IEEE_EXTREMELY_INVERSE = "IEEE_EXTREMELY_INVERSE"
    DEFINITE_TIME = "DEFINITE_TIME"
    INSTANTANEOUS = "INSTANTANEOUS"


class RelayRole(StrEnum):
    """Relay role in the protection hierarchy."""

    PRIMARY = "PRIMARY"
    BACKUP = "BACKUP"
    UPSTREAM = "UPSTREAM"
    DOWNSTREAM = "DOWNSTREAM"


class CTConnection(StrEnum):
    """Current-transformer connection type."""

    STAR = "STAR"
    RESIDUAL = "RESIDUAL"
    CORE_BALANCE = "CORE_BALANCE"
    SUMMATION = "SUMMATION"


@dataclass(frozen=True, slots=True)
class CurrentTransformerInput:
    """Immutable CT input for relay calculations."""

    primary_current_a: Decimal
    secondary_current_a: Decimal

    burden_va: Decimal = Decimal("0")
    accuracy_class: str = "5P20"
    connection: CTConnection = CTConnection.STAR

    def __post_init__(self) -> None:
        """Validate and normalize CT inputs."""

        require_positive_decimal(
            "primary_current_a",
            self.primary_current_a,
        )
        require_positive_decimal(
            "secondary_current_a",
            self.secondary_current_a,
        )
        require_non_negative_decimal(
            "burden_va",
            self.burden_va,
        )

        object.__setattr__(
            self,
            "accuracy_class",
            normalize_required_text(
                "accuracy_class",
                self.accuracy_class,
            ),
        )

        if not isinstance(
            self.connection,
            CTConnection,
        ):
            raise TypeError("connection must be a CTConnection value")

        if self.secondary_current_a not in {
            Decimal("1"),
            Decimal("5"),
        }:
            raise ValueError("secondary_current_a must be 1 A or 5 A")

    @property
    def ratio(self) -> Decimal:
        """Return CT primary-to-secondary ratio."""

        return self.primary_current_a / self.secondary_current_a


@dataclass(frozen=True, slots=True)
class RelayPickupSettings:
    """Relay pickup and timing settings."""

    pickup_current_a: Decimal
    time_multiplier: Decimal = Decimal("1")

    definite_time_delay_s: Decimal | None = None
    instantaneous_pickup_a: Decimal | None = None
    instantaneous_delay_s: Decimal = Decimal("0")

    reset_ratio: Decimal = Decimal("0.95")

    def __post_init__(self) -> None:
        """Validate relay pickup and timing settings."""

        require_positive_decimal(
            "pickup_current_a",
            self.pickup_current_a,
        )
        require_positive_decimal(
            "time_multiplier",
            self.time_multiplier,
        )

        if self.definite_time_delay_s is not None:
            require_non_negative_decimal(
                "definite_time_delay_s",
                self.definite_time_delay_s,
            )

        if self.instantaneous_pickup_a is not None:
            require_positive_decimal(
                "instantaneous_pickup_a",
                self.instantaneous_pickup_a,
            )

        require_non_negative_decimal(
            "instantaneous_delay_s",
            self.instantaneous_delay_s,
        )

        require_positive_decimal(
            "reset_ratio",
            self.reset_ratio,
        )

        if self.reset_ratio > Decimal("1"):
            raise ValueError("reset_ratio must not exceed 1")

        if self.instantaneous_pickup_a is None and self.instantaneous_delay_s != Decimal("0"):
            raise ValueError("instantaneous_delay_s requires instantaneous_pickup_a")


@dataclass(frozen=True, slots=True)
class RelayCurveInput:
    """Relay time-current curve definition."""

    family: RelayCurveFamily
    settings: RelayPickupSettings

    minimum_operating_time_s: Decimal = Decimal("0")
    maximum_operating_time_s: Decimal | None = None

    manufacturer_curve_code: str | None = None
    reference_document: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize relay curve input."""

        if not isinstance(
            self.family,
            RelayCurveFamily,
        ):
            raise TypeError("family must be a RelayCurveFamily value")

        if not isinstance(
            self.settings,
            RelayPickupSettings,
        ):
            raise TypeError("settings must be a RelayPickupSettings record")

        require_non_negative_decimal(
            "minimum_operating_time_s",
            self.minimum_operating_time_s,
        )

        if self.maximum_operating_time_s is not None:
            require_positive_decimal(
                "maximum_operating_time_s",
                self.maximum_operating_time_s,
            )

            if self.maximum_operating_time_s < self.minimum_operating_time_s:
                raise ValueError(
                    "maximum_operating_time_s must not be below minimum_operating_time_s"
                )

        for field_name in (
            "manufacturer_curve_code",
            "reference_document",
            "notes",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(
                    field_name,
                    getattr(self, field_name),
                ),
            )

        if (
            self.family is RelayCurveFamily.DEFINITE_TIME
            and self.settings.definite_time_delay_s is None
        ):
            raise ValueError("DEFINITE_TIME curve requires definite_time_delay_s")


@dataclass(frozen=True, slots=True)
class ProtectionRelayInput:
    """Immutable protection relay engineering input."""

    code: str
    name: str

    function: RelayFunction
    role: RelayRole

    ct: CurrentTransformerInput
    curve: RelayCurveInput

    protected_equipment_code: str
    breaker_code: str | None = None

    grading_margin_s: Decimal = Decimal("0.30")
    coordination_group: str | None = None

    manufacturer: str | None = None
    model: str | None = None
    standard_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize relay engineering input."""

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
            "protected_equipment_code",
            normalize_required_text(
                "protected_equipment_code",
                self.protected_equipment_code,
            ),
        )

        for field_name in (
            "breaker_code",
            "coordination_group",
            "manufacturer",
            "model",
            "standard_reference",
            "notes",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(
                    field_name,
                    getattr(self, field_name),
                ),
            )

        if not isinstance(
            self.function,
            RelayFunction,
        ):
            raise TypeError("function must be a RelayFunction value")

        if not isinstance(
            self.role,
            RelayRole,
        ):
            raise TypeError("role must be a RelayRole value")

        if not isinstance(
            self.ct,
            CurrentTransformerInput,
        ):
            raise TypeError("ct must be a CurrentTransformerInput record")

        if not isinstance(
            self.curve,
            RelayCurveInput,
        ):
            raise TypeError("curve must be a RelayCurveInput record")

        require_non_negative_decimal(
            "grading_margin_s",
            self.grading_margin_s,
        )


@dataclass(frozen=True, slots=True)
class RelayCoordinationStudyInput:
    """Immutable multi-relay coordination study input."""

    code: str
    name: str

    fault_current_a: Decimal
    relays: tuple[ProtectionRelayInput, ...]

    minimum_grading_margin_s: Decimal = Decimal("0.30")
    maximum_operating_time_s: Decimal | None = None

    standard_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize relay coordination study."""

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

        for field_name in (
            "standard_reference",
            "notes",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(
                    field_name,
                    getattr(self, field_name),
                ),
            )

        require_positive_decimal(
            "fault_current_a",
            self.fault_current_a,
        )
        require_non_negative_decimal(
            "minimum_grading_margin_s",
            self.minimum_grading_margin_s,
        )

        if self.maximum_operating_time_s is not None:
            require_positive_decimal(
                "maximum_operating_time_s",
                self.maximum_operating_time_s,
            )

        if not isinstance(
            self.relays,
            tuple,
        ):
            raise TypeError("relays must be a tuple")

        if len(self.relays) < 2:
            raise ValueError("relay coordination study requires at least two relays")

        if not all(
            isinstance(
                relay,
                ProtectionRelayInput,
            )
            for relay in self.relays
        ):
            raise TypeError("relays must contain only ProtectionRelayInput records")

        relay_codes = tuple(relay.code for relay in self.relays)

        if len(relay_codes) != len(set(relay_codes)):
            raise ValueError("relay codes must be unique")


__all__ = [
    "CTConnection",
    "CurrentTransformerInput",
    "ProtectionRelayInput",
    "RelayCoordinationStudyInput",
    "RelayCurveFamily",
    "RelayCurveInput",
    "RelayFunction",
    "RelayPickupSettings",
    "RelayRole",
]
