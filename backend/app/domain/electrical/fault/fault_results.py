"""
Immutable short-circuit and earth-fault engineering results.
KESE-S2-M15
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.fault.fault_models import (
    FaultSourceType,
    FaultType,
    ShortCircuitCase,
    SourceRepresentation,
)
from app.domain.electrical.sources.common import (
    normalize_optional_text,
    normalize_required_text,
    require_non_negative_decimal,
    require_positive_decimal,
)


class FaultResultStatus(StrEnum):
    """Overall outcome of a short-circuit calculation."""

    CALCULATED = "CALCULATED"
    WARNING = "WARNING"
    INDETERMINATE = "INDETERMINATE"


class FaultSequence(StrEnum):
    """Symmetrical sequence represented by an equivalent network result."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    ZERO = "ZERO"


class FaultWarningSeverity(StrEnum):
    """Engineering consequence assigned to a fault-study warning."""

    WARNING = "WARNING"
    ERROR = "ERROR"


class FaultWarningCode(StrEnum):
    """Machine-readable short-circuit and earth-fault warning codes."""

    NO_FAULT_CURRENT_PATH = "NO_FAULT_CURRENT_PATH"
    ZERO_SEQUENCE_PATH_BLOCKED = "ZERO_SEQUENCE_PATH_BLOCKED"
    INCOMPLETE_SEQUENCE_DATA = "INCOMPLETE_SEQUENCE_DATA"
    CURRENT_INJECTION_APPROXIMATION = "CURRENT_INJECTION_APPROXIMATION"
    PEAK_CURRENT_NOT_EVALUATED = "PEAK_CURRENT_NOT_EVALUATED"
    BREAKING_CURRENT_NOT_EVALUATED = "BREAKING_CURRENT_NOT_EVALUATED"
    STEADY_STATE_CURRENT_NOT_EVALUATED = "STEADY_STATE_CURRENT_NOT_EVALUATED"
    THERMAL_CURRENT_NOT_EVALUATED = "THERMAL_CURRENT_NOT_EVALUATED"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    CALCULATION_FAILED = "CALCULATION_FAILED"


_UNBALANCED_FAULT_TYPES = {
    FaultType.TWO_PHASE,
    FaultType.TWO_PHASE_TO_EARTH,
    FaultType.SINGLE_PHASE_TO_EARTH,
}

_EARTH_FAULT_TYPES = {
    FaultType.TWO_PHASE_TO_EARTH,
    FaultType.SINGLE_PHASE_TO_EARTH,
}


def _require_boolean(field_name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean")


def _require_optional_non_negative_decimal(
    field_name: str,
    value: Decimal | None,
) -> None:
    if value is not None:
        require_non_negative_decimal(field_name, value)


def _normalize_unique_codes(
    field_name: str,
    values: tuple[str, ...],
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple")

    normalized_values = tuple(normalize_required_text(field_name, value) for value in values)
    if len(normalized_values) != len(set(normalized_values)):
        raise ValueError(f"{field_name} values must be unique")
    return normalized_values


@dataclass(frozen=True, slots=True)
class FaultEngineeringWarning:
    """Structured warning emitted by a fault-current calculation."""

    code: FaultWarningCode
    severity: FaultWarningSeverity
    message: str
    reference_code: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the engineering warning."""

        if not isinstance(self.code, FaultWarningCode):
            raise TypeError("code must be a FaultWarningCode value")
        if not isinstance(self.severity, FaultWarningSeverity):
            raise TypeError("severity must be a FaultWarningSeverity value")

        object.__setattr__(
            self,
            "message",
            normalize_required_text("message", self.message),
        )
        object.__setattr__(
            self,
            "reference_code",
            normalize_optional_text("reference_code", self.reference_code),
        )


@dataclass(frozen=True, slots=True)
class EquivalentSequenceImpedanceResult:
    """Auditable equivalent impedance or an explicit blocked sequence path."""

    sequence: FaultSequence
    available: bool
    resistance_ohm: Decimal | None
    reactance_ohm: Decimal | None
    path_reference_codes: tuple[str, ...] = ()
    blocking_reference_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate available and blocked sequence-network representations."""

        if not isinstance(self.sequence, FaultSequence):
            raise TypeError("sequence must be a FaultSequence value")
        _require_boolean("available", self.available)

        object.__setattr__(
            self,
            "path_reference_codes",
            _normalize_unique_codes(
                "path_reference_codes",
                self.path_reference_codes,
            ),
        )
        object.__setattr__(
            self,
            "blocking_reference_codes",
            _normalize_unique_codes(
                "blocking_reference_codes",
                self.blocking_reference_codes,
            ),
        )

        if set(self.path_reference_codes) & set(self.blocking_reference_codes):
            raise ValueError("path and blocking reference codes must not overlap")

        if self.available:
            if self.resistance_ohm is None or self.reactance_ohm is None:
                raise ValueError("available sequence result requires resistance and reactance")
            require_non_negative_decimal("resistance_ohm", self.resistance_ohm)
            require_non_negative_decimal("reactance_ohm", self.reactance_ohm)
            if self.resistance_ohm == self.reactance_ohm == Decimal("0"):
                raise ValueError("available sequence impedance must not be zero")
            if self.blocking_reference_codes:
                raise ValueError("available sequence result cannot define blocking references")
        else:
            if self.resistance_ohm is not None or self.reactance_ohm is not None:
                raise ValueError("unavailable sequence result cannot define impedance values")
            if not self.blocking_reference_codes:
                raise ValueError("unavailable sequence result requires blocking references")


@dataclass(frozen=True, slots=True)
class FaultSourceContributionResult:
    """Calculated contribution or explicit exclusion of one fault source."""

    source_code: str
    source_type: FaultSourceType
    representation: SourceRepresentation
    included: bool
    initial_symmetrical_current_ka: Decimal
    peak_current_ka: Decimal | None
    exclusion_reason: str | None = None

    def __post_init__(self) -> None:
        """Validate source participation and calculated current duties."""

        object.__setattr__(
            self,
            "source_code",
            normalize_required_text("source_code", self.source_code),
        )
        object.__setattr__(
            self,
            "exclusion_reason",
            normalize_optional_text("exclusion_reason", self.exclusion_reason),
        )

        if not isinstance(self.source_type, FaultSourceType):
            raise TypeError("source_type must be a FaultSourceType value")
        if not isinstance(self.representation, SourceRepresentation):
            raise TypeError("representation must be a SourceRepresentation value")
        _require_boolean("included", self.included)

        require_non_negative_decimal(
            "initial_symmetrical_current_ka",
            self.initial_symmetrical_current_ka,
        )
        _require_optional_non_negative_decimal(
            "peak_current_ka",
            self.peak_current_ka,
        )
        if (
            self.peak_current_ka is not None
            and self.peak_current_ka < self.initial_symmetrical_current_ka
        ):
            raise ValueError("source peak_current_ka must not be below initial symmetrical current")

        if self.included:
            if self.initial_symmetrical_current_ka <= Decimal("0"):
                raise ValueError("included source requires a positive current contribution")
            if self.exclusion_reason is not None:
                raise ValueError("included source cannot define an exclusion reason")
        else:
            if self.initial_symmetrical_current_ka != Decimal("0"):
                raise ValueError("excluded source must have zero current contribution")
            if self.peak_current_ka is not None:
                raise ValueError("excluded source cannot define peak_current_ka")
            if self.exclusion_reason is None:
                raise ValueError("excluded source requires an exclusion reason")


@dataclass(frozen=True, slots=True)
class ShortCircuitStudyResult:
    """Complete immutable IEC 60909 short-circuit study result."""

    study_code: str
    study_name: str
    calculation_case: ShortCircuitCase
    fault_bus_code: str
    fault_type: FaultType
    nominal_voltage_v: Decimal
    frequency_hz: Decimal
    status: FaultResultStatus

    initial_symmetrical_short_circuit_current_ka: Decimal | None
    peak_short_circuit_current_ka: Decimal | None
    symmetrical_breaking_current_ka: Decimal | None
    steady_state_short_circuit_current_ka: Decimal | None
    thermal_equivalent_short_circuit_current_ka: Decimal | None
    earth_fault_current_ka: Decimal | None
    kappa_factor: Decimal | None
    x_r_ratio: Decimal | None
    clearing_time_s: Decimal | None

    sequence_results: tuple[EquivalentSequenceImpedanceResult, ...]
    source_contributions: tuple[FaultSourceContributionResult, ...]
    warnings: tuple[FaultEngineeringWarning, ...] = ()

    standard_reference: str = "IEC 60909-0:2026"
    earth_current_reference: str = "IEC 60909-3:2009"
    operating_state_code: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate current duties, sequence coverage, sources, and status."""

        for field_name in ("study_code", "study_name", "fault_bus_code"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(field_name, getattr(self, field_name)),
            )
        for field_name in ("standard_reference", "earth_current_reference"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(field_name, getattr(self, field_name)),
            )
        for field_name in ("operating_state_code", "notes"):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(field_name, getattr(self, field_name)),
            )

        if not isinstance(self.calculation_case, ShortCircuitCase):
            raise TypeError("calculation_case must be a ShortCircuitCase value")
        if not isinstance(self.fault_type, FaultType):
            raise TypeError("fault_type must be a FaultType value")
        if not isinstance(self.status, FaultResultStatus):
            raise TypeError("status must be a FaultResultStatus value")

        require_positive_decimal("nominal_voltage_v", self.nominal_voltage_v)
        require_positive_decimal("frequency_hz", self.frequency_hz)
        if self.frequency_hz not in {Decimal("50"), Decimal("60")}:
            raise ValueError("frequency_hz must be 50 or 60 for an IEC 60909 result")

        current_fields = (
            "initial_symmetrical_short_circuit_current_ka",
            "peak_short_circuit_current_ka",
            "symmetrical_breaking_current_ka",
            "steady_state_short_circuit_current_ka",
            "thermal_equivalent_short_circuit_current_ka",
            "earth_fault_current_ka",
        )
        for field_name in current_fields:
            _require_optional_non_negative_decimal(
                field_name,
                getattr(self, field_name),
            )

        _require_optional_non_negative_decimal("x_r_ratio", self.x_r_ratio)
        if self.kappa_factor is not None:
            require_positive_decimal("kappa_factor", self.kappa_factor)
            if not Decimal("1") <= self.kappa_factor <= Decimal("2"):
                raise ValueError("kappa_factor must be between 1 and 2")
        if self.clearing_time_s is not None:
            require_positive_decimal("clearing_time_s", self.clearing_time_s)

        collections: tuple[tuple[str, tuple[object, ...], type[object]], ...] = (
            (
                "sequence_results",
                self.sequence_results,
                EquivalentSequenceImpedanceResult,
            ),
            (
                "source_contributions",
                self.source_contributions,
                FaultSourceContributionResult,
            ),
            ("warnings", self.warnings, FaultEngineeringWarning),
        )
        for field_name, records, record_type in collections:
            if not isinstance(records, tuple):
                raise TypeError(f"{field_name} must be a tuple")
            if not all(isinstance(record, record_type) for record in records):
                raise TypeError(f"{field_name} must contain only {record_type.__name__} records")

        if not self.sequence_results:
            raise ValueError("a fault study result requires sequence results")

        sequence_by_type = {result.sequence: result for result in self.sequence_results}
        source_codes = tuple(contribution.source_code for contribution in self.source_contributions)
        warning_keys = tuple((warning.code, warning.reference_code) for warning in self.warnings)
        if len(sequence_by_type) != len(self.sequence_results):
            raise ValueError("sequence result types must be unique")
        if len(source_codes) != len(set(source_codes)):
            raise ValueError("source contribution codes must be unique")
        if len(warning_keys) != len(set(warning_keys)):
            raise ValueError("warning code and reference combinations must be unique")

        required_sequences = {FaultSequence.POSITIVE}
        if self.fault_type in _UNBALANCED_FAULT_TYPES:
            required_sequences.add(FaultSequence.NEGATIVE)
        if self.fault_type in _EARTH_FAULT_TYPES:
            required_sequences.add(FaultSequence.ZERO)
        if not required_sequences.issubset(sequence_by_type):
            raise ValueError("fault result is missing a required sequence result")

        has_error = any(warning.severity is FaultWarningSeverity.ERROR for warning in self.warnings)
        expected_status = FaultResultStatus.CALCULATED
        if has_error:
            expected_status = FaultResultStatus.INDETERMINATE
        elif self.warnings:
            expected_status = FaultResultStatus.WARNING
        if self.status is not expected_status:
            raise ValueError("fault result status does not match its warnings")

        duty_fields = (
            self.initial_symmetrical_short_circuit_current_ka,
            self.peak_short_circuit_current_ka,
            self.symmetrical_breaking_current_ka,
            self.steady_state_short_circuit_current_ka,
            self.thermal_equivalent_short_circuit_current_ka,
            self.earth_fault_current_ka,
            self.kappa_factor,
            self.x_r_ratio,
        )
        if self.status is FaultResultStatus.INDETERMINATE:
            if any(value is not None for value in duty_fields):
                raise ValueError("INDETERMINATE result must not contain calculated current duties")
            if any(contribution.included for contribution in self.source_contributions):
                raise ValueError(
                    "INDETERMINATE result cannot contain included source contributions"
                )
            return

        initial_current = self.initial_symmetrical_short_circuit_current_ka
        if initial_current is None:
            raise ValueError("calculated fault result requires initial symmetrical current")

        if self.fault_type in _EARTH_FAULT_TYPES:
            if self.earth_fault_current_ka is None:
                raise ValueError("earth-fault result requires earth_fault_current_ka")
        elif self.earth_fault_current_ka is not None:
            raise ValueError("non-earth fault result cannot define earth_fault_current_ka")

        peak_values = (
            self.peak_short_circuit_current_ka,
            self.kappa_factor,
            self.x_r_ratio,
        )
        if any(value is None for value in peak_values) and any(
            value is not None for value in peak_values
        ):
            raise ValueError("peak current, kappa factor, and X/R ratio must be provided together")
        if (
            self.peak_short_circuit_current_ka is not None
            and self.peak_short_circuit_current_ka < initial_current
        ):
            raise ValueError("peak short-circuit current must not be below initial current")

        thermal_values = (
            self.thermal_equivalent_short_circuit_current_ka,
            self.clearing_time_s,
        )
        if any(value is None for value in thermal_values) and any(
            value is not None for value in thermal_values
        ):
            raise ValueError("thermal current and clearing time must be provided together")

        included_sources = tuple(
            contribution for contribution in self.source_contributions if contribution.included
        )
        if initial_current > Decimal("0") and not included_sources:
            raise ValueError("positive fault current requires an included source contribution")
        if initial_current == Decimal("0"):
            if included_sources:
                raise ValueError("zero fault current cannot contain included source contributions")
            warning_codes = {warning.code for warning in self.warnings}
            if FaultWarningCode.NO_FAULT_CURRENT_PATH not in warning_codes:
                raise ValueError("zero fault current requires NO_FAULT_CURRENT_PATH warning")


__all__ = [
    "EquivalentSequenceImpedanceResult",
    "FaultEngineeringWarning",
    "FaultResultStatus",
    "FaultSequence",
    "FaultSourceContributionResult",
    "FaultWarningCode",
    "FaultWarningSeverity",
    "ShortCircuitStudyResult",
]
