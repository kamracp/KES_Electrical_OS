"""
Immutable results for cable sizing and ampacity engineering.
KESE-S2-M13
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


class CableCheckStatus(StrEnum):
    """Outcome of an individual cable engineering check."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CableSizingStatus(StrEnum):
    """Overall cable sizing outcome."""

    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NO_STANDARD_SIZE_AVAILABLE = "NO_STANDARD_SIZE_AVAILABLE"


class CableWarningCode(StrEnum):
    """Machine-readable cable engineering warning codes."""

    AMPACITY_INADEQUATE = "AMPACITY_INADEQUATE"
    VOLTAGE_DROP_EXCEEDED = "VOLTAGE_DROP_EXCEEDED"
    SHORT_CIRCUIT_WITHSTAND_INADEQUATE = "SHORT_CIRCUIT_WITHSTAND_INADEQUATE"
    NEUTRAL_SIZE_INADEQUATE = "NEUTRAL_SIZE_INADEQUATE"
    PROTECTIVE_CONDUCTOR_INADEQUATE = "PROTECTIVE_CONDUCTOR_INADEQUATE"
    HIGH_TOTAL_DERATING = "HIGH_TOTAL_DERATING"
    PARALLEL_CABLE_CURRENT_SHARING = "PARALLEL_CABLE_CURRENT_SHARING"
    SOIL_DATA_REQUIRED = "SOIL_DATA_REQUIRED"
    NO_STANDARD_SIZE_AVAILABLE = "NO_STANDARD_SIZE_AVAILABLE"


@dataclass(frozen=True, slots=True)
class CableEngineeringWarning:
    """Structured warning emitted by the cable sizing engine."""

    code: CableWarningCode
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize an engineering warning."""

        if not isinstance(self.code, CableWarningCode):
            raise TypeError("code must be a CableWarningCode value")

        object.__setattr__(
            self,
            "message",
            normalize_required_text("message", self.message),
        )
        object.__setattr__(
            self,
            "field_name",
            normalize_optional_text("field_name", self.field_name),
        )


@dataclass(frozen=True, slots=True)
class CableAmpacityResult:
    """Thermal current-carrying result for one cable run configuration."""

    tabulated_ampacity_a_per_run: Decimal
    combined_derating_factor: Decimal
    derated_ampacity_a_per_run: Decimal
    parallel_runs: int
    total_installed_ampacity_a: Decimal
    design_current_a: Decimal
    required_tabulated_ampacity_a_per_run: Decimal
    utilization_ratio: Decimal
    status: CableCheckStatus

    def __post_init__(self) -> None:
        """Validate the ampacity calculation result."""

        for field_name in (
            "tabulated_ampacity_a_per_run",
            "derated_ampacity_a_per_run",
            "total_installed_ampacity_a",
            "design_current_a",
            "required_tabulated_ampacity_a_per_run",
            "utilization_ratio",
        ):
            require_positive_decimal(field_name, getattr(self, field_name))

        require_ratio("combined_derating_factor", self.combined_derating_factor)

        if not isinstance(self.parallel_runs, int) or isinstance(self.parallel_runs, bool):
            raise TypeError("parallel_runs must be an integer")
        if self.parallel_runs < 1:
            raise ValueError("parallel_runs must be at least 1")

        if not isinstance(self.status, CableCheckStatus):
            raise TypeError("status must be a CableCheckStatus value")
        if self.status is CableCheckStatus.NOT_APPLICABLE:
            raise ValueError("ampacity status must be PASS or FAIL")


@dataclass(frozen=True, slots=True)
class CableVoltageDropResult:
    """Steady-state cable voltage-drop result."""

    resistance_ohm_per_km: Decimal
    reactance_ohm_per_km: Decimal
    voltage_drop_v: Decimal
    voltage_drop_percent: Decimal
    allowable_voltage_drop_percent: Decimal
    status: CableCheckStatus

    def __post_init__(self) -> None:
        """Validate the voltage-drop result."""

        for field_name in (
            "resistance_ohm_per_km",
            "reactance_ohm_per_km",
            "voltage_drop_v",
            "voltage_drop_percent",
        ):
            require_non_negative_decimal(field_name, getattr(self, field_name))

        require_positive_decimal(
            "allowable_voltage_drop_percent",
            self.allowable_voltage_drop_percent,
        )

        if self.allowable_voltage_drop_percent > Decimal("100"):
            raise ValueError("allowable_voltage_drop_percent must not exceed 100")

        if not isinstance(self.status, CableCheckStatus):
            raise TypeError("status must be a CableCheckStatus value")
        if self.status is CableCheckStatus.NOT_APPLICABLE:
            raise ValueError("voltage-drop status must be PASS or FAIL")


@dataclass(frozen=True, slots=True)
class CableShortCircuitResult:
    """Adiabatic short-circuit withstand result."""

    fault_current_ka: Decimal | None
    fault_duration_s: Decimal | None
    material_constant_k: Decimal | None
    required_area_mm2: Decimal | None
    selected_area_mm2: Decimal
    withstand_current_ka: Decimal | None
    status: CableCheckStatus

    def __post_init__(self) -> None:
        """Validate the short-circuit withstand result."""

        require_positive_decimal("selected_area_mm2", self.selected_area_mm2)

        optional_values = (
            ("fault_current_ka", self.fault_current_ka),
            ("fault_duration_s", self.fault_duration_s),
            ("material_constant_k", self.material_constant_k),
            ("required_area_mm2", self.required_area_mm2),
            ("withstand_current_ka", self.withstand_current_ka),
        )
        provided_count = sum(value is not None for _, value in optional_values)

        if provided_count not in {0, len(optional_values)}:
            raise ValueError("short-circuit calculation values must be provided together")

        for field_name, value in optional_values:
            if value is not None:
                require_positive_decimal(field_name, value)

        if not isinstance(self.status, CableCheckStatus):
            raise TypeError("status must be a CableCheckStatus value")

        if provided_count == 0 and self.status is not CableCheckStatus.NOT_APPLICABLE:
            raise ValueError("missing short-circuit values require NOT_APPLICABLE status")
        if provided_count > 0 and self.status is CableCheckStatus.NOT_APPLICABLE:
            raise ValueError("provided short-circuit values require PASS or FAIL status")


@dataclass(frozen=True, slots=True)
class CableConductorSizingResult:
    """Selected phase, neutral, and protective conductor sizes."""

    phase_area_mm2: Decimal
    neutral_area_mm2: Decimal | None
    protective_area_mm2: Decimal | None
    parallel_runs: int
    phase_conductors_per_run: int
    neutral_status: CableCheckStatus
    protective_status: CableCheckStatus

    def __post_init__(self) -> None:
        """Validate selected conductor sizes."""

        require_positive_decimal("phase_area_mm2", self.phase_area_mm2)

        for field_name in ("neutral_area_mm2", "protective_area_mm2"):
            value = getattr(self, field_name)
            if value is not None:
                require_positive_decimal(field_name, value)

        for field_name, value in (
            ("parallel_runs", self.parallel_runs),
            ("phase_conductors_per_run", self.phase_conductors_per_run),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value < 1:
                raise ValueError(f"{field_name} must be at least 1")

        for field_name, value in (
            ("neutral_status", self.neutral_status),
            ("protective_status", self.protective_status),
        ):
            if not isinstance(value, CableCheckStatus):
                raise TypeError(f"{field_name} must be a CableCheckStatus value")

        if (
            self.neutral_area_mm2 is None
            and self.neutral_status is not CableCheckStatus.NOT_APPLICABLE
        ):
            raise ValueError("missing neutral area requires NOT_APPLICABLE neutral status")
        if (
            self.neutral_area_mm2 is not None
            and self.neutral_status is CableCheckStatus.NOT_APPLICABLE
        ):
            raise ValueError("selected neutral area requires PASS or FAIL neutral status")

        if (
            self.protective_area_mm2 is None
            and self.protective_status is not CableCheckStatus.NOT_APPLICABLE
        ):
            raise ValueError("missing protective area requires NOT_APPLICABLE protective status")
        if (
            self.protective_area_mm2 is not None
            and self.protective_status is CableCheckStatus.NOT_APPLICABLE
        ):
            raise ValueError("selected protective area requires PASS or FAIL protective status")


@dataclass(frozen=True, slots=True)
class CableSizingResult:
    """Complete auditable cable sizing result."""

    study_code: str
    status: CableSizingStatus
    conductor: CableConductorSizingResult | None
    ampacity: CableAmpacityResult | None
    voltage_drop: CableVoltageDropResult | None
    short_circuit: CableShortCircuitResult | None
    warnings: tuple[CableEngineeringWarning, ...] = ()

    governing_criterion: str | None = None
    standard_reference: str = "IEC 60364-5-52"
    ampacity_reference: str = "IEC 60287"

    def __post_init__(self) -> None:
        """Validate and normalize the complete cable sizing result."""

        object.__setattr__(
            self,
            "study_code",
            normalize_required_text("study_code", self.study_code),
        )
        object.__setattr__(
            self,
            "governing_criterion",
            normalize_optional_text("governing_criterion", self.governing_criterion),
        )
        object.__setattr__(
            self,
            "standard_reference",
            normalize_required_text("standard_reference", self.standard_reference),
        )
        object.__setattr__(
            self,
            "ampacity_reference",
            normalize_required_text("ampacity_reference", self.ampacity_reference),
        )

        if not isinstance(self.status, CableSizingStatus):
            raise TypeError("status must be a CableSizingStatus value")

        result_fields = (
            ("conductor", self.conductor, CableConductorSizingResult),
            ("ampacity", self.ampacity, CableAmpacityResult),
            ("voltage_drop", self.voltage_drop, CableVoltageDropResult),
            ("short_circuit", self.short_circuit, CableShortCircuitResult),
        )
        for field_name, value, result_type in result_fields:
            if value is not None and not isinstance(value, result_type):
                raise TypeError(f"{field_name} must be a {result_type.__name__} result or None")

        if not isinstance(self.warnings, tuple):
            raise TypeError("warnings must be a tuple")
        if not all(isinstance(warning, CableEngineeringWarning) for warning in self.warnings):
            raise TypeError("warnings must contain only CableEngineeringWarning records")

        warning_codes = tuple(warning.code for warning in self.warnings)
        if len(warning_codes) != len(set(warning_codes)):
            raise ValueError("warning codes must be unique")

        detailed_results = (
            self.conductor,
            self.ampacity,
            self.voltage_drop,
            self.short_circuit,
        )
        if self.status is CableSizingStatus.NO_STANDARD_SIZE_AVAILABLE:
            if any(result is not None for result in detailed_results):
                raise ValueError(
                    "NO_STANDARD_SIZE_AVAILABLE result cannot contain selected cable results"
                )
            if CableWarningCode.NO_STANDARD_SIZE_AVAILABLE not in warning_codes:
                raise ValueError("NO_STANDARD_SIZE_AVAILABLE status requires its warning code")
        elif any(result is None for result in detailed_results):
            raise ValueError("COMPLIANT and NON_COMPLIANT results require all detailed results")

        if self.status is CableSizingStatus.COMPLIANT:
            assert self.conductor is not None
            assert self.ampacity is not None
            assert self.voltage_drop is not None
            assert self.short_circuit is not None
            check_statuses = (
                self.conductor.neutral_status,
                self.conductor.protective_status,
                self.ampacity.status,
                self.voltage_drop.status,
                self.short_circuit.status,
            )
            if CableCheckStatus.FAIL in check_statuses:
                raise ValueError("COMPLIANT result cannot contain a failed engineering check")


__all__ = [
    "CableAmpacityResult",
    "CableCheckStatus",
    "CableConductorSizingResult",
    "CableEngineeringWarning",
    "CableShortCircuitResult",
    "CableSizingResult",
    "CableSizingStatus",
    "CableVoltageDropResult",
    "CableWarningCode",
]
