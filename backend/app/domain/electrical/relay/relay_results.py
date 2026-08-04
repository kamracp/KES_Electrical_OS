"""
Result models for protection relay and TCC engineering.
KESE-S2-M12
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.relay.relay_models import (
    RelayCurveFamily,
    RelayFunction,
    RelayRole,
)
from app.domain.electrical.sources.common import (
    normalize_required_text,
)


class RelayOperatingStatus(StrEnum):
    """Relay operating-point status."""

    OPERATED = "OPERATED"
    INSTANTANEOUS = "INSTANTANEOUS"
    BELOW_PICKUP = "BELOW_PICKUP"
    INVALID = "INVALID"


class RelayCoordinationStatus(StrEnum):
    """Overall relay coordination status."""

    COORDINATED = "COORDINATED"
    WARNING = "WARNING"
    NOT_COORDINATED = "NOT_COORDINATED"


class RelayWarningCode(StrEnum):
    """Structured relay engineering warning codes."""

    BELOW_PICKUP = "BELOW_PICKUP"
    OPERATING_TIME_EXCEEDED = "OPERATING_TIME_EXCEEDED"
    GRADING_MARGIN_LOW = "GRADING_MARGIN_LOW"
    CURVE_CROSSING_DETECTED = "CURVE_CROSSING_DETECTED"
    INSTANTANEOUS_OVERLAP = "INSTANTANEOUS_OVERLAP"
    INVALID_CURVE_INPUT = "INVALID_CURVE_INPUT"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class RelayWarning:
    """Structured relay engineering warning."""

    code: RelayWarningCode
    message: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.code,
            RelayWarningCode,
        ):
            raise TypeError("code must be a RelayWarningCode value")

        object.__setattr__(
            self,
            "message",
            normalize_required_text(
                "message",
                self.message,
            ),
        )


@dataclass(frozen=True, slots=True)
class RelayOperatingPointResult:
    """Calculated operating point for one relay."""

    relay_code: str
    relay_name: str

    function: RelayFunction
    role: RelayRole
    curve_family: RelayCurveFamily

    fault_current_a: Decimal
    pickup_current_a: Decimal
    current_multiple: Decimal

    operating_time_s: Decimal | None
    instantaneous_operation: bool

    status: RelayOperatingStatus
    warnings: tuple[RelayWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relay_code",
            normalize_required_text(
                "relay_code",
                self.relay_code,
            ),
        )
        object.__setattr__(
            self,
            "relay_name",
            normalize_required_text(
                "relay_name",
                self.relay_name,
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
            self.curve_family,
            RelayCurveFamily,
        ):
            raise TypeError("curve_family must be a RelayCurveFamily value")

        if not isinstance(
            self.instantaneous_operation,
            bool,
        ):
            raise TypeError("instantaneous_operation must be a boolean")

        if not isinstance(
            self.status,
            RelayOperatingStatus,
        ):
            raise TypeError("status must be a RelayOperatingStatus value")

        if (
            self.status
            in {
                RelayOperatingStatus.OPERATED,
                RelayOperatingStatus.INSTANTANEOUS,
            }
            and self.operating_time_s is None
        ):
            raise ValueError("operated relay result requires operating_time_s")

        if self.status is RelayOperatingStatus.BELOW_PICKUP and self.operating_time_s is not None:
            raise ValueError("BELOW_PICKUP result must not contain operating_time_s")

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError("warnings must be a tuple")

        if not all(
            isinstance(
                warning,
                RelayWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError("warnings must contain only RelayWarning records")

        warning_codes = tuple(warning.code for warning in self.warnings)

        if len(warning_codes) != len(set(warning_codes)):
            raise ValueError("operating-point warning codes must be unique")


@dataclass(frozen=True, slots=True)
class RelayPairCoordinationResult:
    """Coordination result for one downstream-upstream relay pair."""

    downstream_relay_code: str
    upstream_relay_code: str

    downstream_operating_time_s: Decimal
    upstream_operating_time_s: Decimal

    grading_margin_s: Decimal
    required_grading_margin_s: Decimal

    coordinated: bool
    curve_crossing_detected: bool
    instantaneous_overlap: bool

    warnings: tuple[RelayWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "downstream_relay_code",
            normalize_required_text(
                "downstream_relay_code",
                self.downstream_relay_code,
            ),
        )
        object.__setattr__(
            self,
            "upstream_relay_code",
            normalize_required_text(
                "upstream_relay_code",
                self.upstream_relay_code,
            ),
        )

        for field_name, value in {
            "coordinated": self.coordinated,
            "curve_crossing_detected": (self.curve_crossing_detected),
            "instantaneous_overlap": (self.instantaneous_overlap),
        }.items():
            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be a boolean")

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError("warnings must be a tuple")

        if not all(
            isinstance(
                warning,
                RelayWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError("warnings must contain only RelayWarning records")

        warning_codes = tuple(warning.code for warning in self.warnings)

        if len(warning_codes) != len(set(warning_codes)):
            raise ValueError("relay-pair warning codes must be unique")


@dataclass(frozen=True, slots=True)
class RelayCoordinationStudyResult:
    """Immutable multi-relay coordination study result."""

    code: str
    name: str

    fault_current_a: Decimal

    evaluated_relays: int
    evaluated_pairs: int
    coordinated_pairs: int

    operating_points: tuple[
        RelayOperatingPointResult,
        ...,
    ]
    pair_results: tuple[
        RelayPairCoordinationResult,
        ...,
    ]

    maximum_operating_time_s: Decimal | None
    minimum_grading_margin_s: Decimal | None

    status: RelayCoordinationStatus
    warnings: tuple[RelayWarning, ...]

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

        for field_name, value in {
            "evaluated_relays": self.evaluated_relays,
            "evaluated_pairs": self.evaluated_pairs,
            "coordinated_pairs": self.coordinated_pairs,
        }.items():
            if isinstance(value, bool) or not isinstance(
                value,
                int,
            ):
                raise TypeError(f"{field_name} must be an integer")

            if value < 0:
                raise ValueError(f"{field_name} must not be negative")

        if self.coordinated_pairs > self.evaluated_pairs:
            raise ValueError("coordinated_pairs must not exceed evaluated_pairs")

        if not isinstance(
            self.operating_points,
            tuple,
        ):
            raise TypeError("operating_points must be a tuple")

        if not all(
            isinstance(
                point,
                RelayOperatingPointResult,
            )
            for point in self.operating_points
        ):
            raise TypeError("operating_points must contain only RelayOperatingPointResult records")

        if len(self.operating_points) != self.evaluated_relays:
            raise ValueError("operating_points count must equal evaluated_relays")

        if not isinstance(
            self.pair_results,
            tuple,
        ):
            raise TypeError("pair_results must be a tuple")

        if not all(
            isinstance(
                result,
                RelayPairCoordinationResult,
            )
            for result in self.pair_results
        ):
            raise TypeError("pair_results must contain only RelayPairCoordinationResult records")

        if len(self.pair_results) != self.evaluated_pairs:
            raise ValueError("pair_results count must equal evaluated_pairs")

        if not isinstance(
            self.status,
            RelayCoordinationStatus,
        ):
            raise TypeError("status must be a RelayCoordinationStatus value")

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError("warnings must be a tuple")

        if not all(
            isinstance(
                warning,
                RelayWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError("warnings must contain only RelayWarning records")

        warning_codes = tuple(warning.code for warning in self.warnings)

        if len(warning_codes) != len(set(warning_codes)):
            raise ValueError("study warning codes must be unique")


__all__ = [
    "RelayCoordinationStatus",
    "RelayCoordinationStudyResult",
    "RelayOperatingPointResult",
    "RelayOperatingStatus",
    "RelayPairCoordinationResult",
    "RelayWarning",
    "RelayWarningCode",
]
