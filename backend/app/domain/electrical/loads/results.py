"""
Result models for electrical load and demand calculations.
KESE-S2-M1
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.loads.models import (
    LoadScenario,
    PhaseSystem,
)


class CalculationStatus(StrEnum):
    """Overall state of a completed calculation."""

    VALID = "VALID"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class LoadWarningCode(StrEnum):
    """Controlled warnings produced by load calculations."""

    ZERO_DEMAND = "ZERO_DEMAND"
    UTILIZATION_FACTOR_NOT_ESTABLISHED = "UTILIZATION_FACTOR_NOT_ESTABLISHED"
    DEMAND_FACTOR_NOT_ESTABLISHED = "DEMAND_FACTOR_NOT_ESTABLISHED"
    EFFICIENCY_NOT_ESTABLISHED = "EFFICIENCY_NOT_ESTABLISHED"
    COINCIDENCE_FACTOR_NOT_ESTABLISHED = "COINCIDENCE_FACTOR_NOT_ESTABLISHED"


NOT_ESTABLISHED_WARNING_CODES = frozenset(
    {
        LoadWarningCode.UTILIZATION_FACTOR_NOT_ESTABLISHED,
        LoadWarningCode.DEMAND_FACTOR_NOT_ESTABLISHED,
        LoadWarningCode.EFFICIENCY_NOT_ESTABLISHED,
        LoadWarningCode.COINCIDENCE_FACTOR_NOT_ESTABLISHED,
    }
)

GROUP_COINCIDENCE_ASSUMPTION = (
    "The group coincidence factor is applied equally to active and reactive demand."
)


@dataclass(frozen=True, slots=True)
class CalculationWarning:
    """Structured engineering calculation warning."""

    code: LoadWarningCode
    message: str

    def __post_init__(self) -> None:
        """Validate warning content."""

        if not isinstance(self.code, LoadWarningCode):
            raise TypeError("code must be a LoadWarningCode value")

        normalized_message = self.message.strip()

        if not normalized_message:
            raise ValueError("warning message must not be empty")

        object.__setattr__(
            self,
            "message",
            normalized_message,
        )


def has_not_established_warning(
    warnings: tuple["CalculationWarning", ...],
) -> bool:
    """Report whether any warning names a factor that is not established."""

    return any(warning.code in NOT_ESTABLISHED_WARNING_CODES for warning in warnings)


def resolve_status(
    warnings: tuple["CalculationWarning", ...],
) -> CalculationStatus:
    """
    Derive the reported status from the warnings.

    A not-established factor outranks every other warning: the figures
    were produced with an assumed 1 and an engineer must establish the
    factor before the result may be used (Master Prompt A15).
    """

    if not warnings:
        return CalculationStatus.VALID

    if has_not_established_warning(warnings):
        return CalculationStatus.REVIEW_REQUIRED

    return CalculationStatus.WARNING


def _require_status_matches_warnings(
    status: CalculationStatus,
    warnings: tuple["CalculationWarning", ...],
) -> None:
    """Keep the reported status consistent with the warning records."""

    if status is CalculationStatus.VALID and warnings:
        raise ValueError("VALID result must not contain warnings")

    if status is CalculationStatus.WARNING:
        if not warnings:
            raise ValueError("WARNING result must contain at least one warning")

        if has_not_established_warning(warnings):
            raise ValueError(
                "WARNING result must not contain a not-established warning; "
                "the status must be REVIEW_REQUIRED"
            )

    if status is CalculationStatus.REVIEW_REQUIRED and not has_not_established_warning(warnings):
        raise ValueError("REVIEW_REQUIRED result must contain at least one not-established warning")


def _require_non_negative_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    """Require an exact, finite, non-negative Decimal."""

    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal")

    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite")

    if value < Decimal("0"):
        raise ValueError(f"{field_name} must not be negative")


@dataclass(frozen=True, slots=True)
class LoadCalculationResult:
    """Calculated electrical values for one load record."""

    load_code: str
    load_name: str
    scenario: LoadScenario
    phase_system: PhaseSystem
    connected_power_kw: Decimal
    utilized_power_kw: Decimal
    demand_power_kw: Decimal
    apparent_power_kva: Decimal
    reactive_power_kvar: Decimal
    design_current_a: Decimal
    status: CalculationStatus = CalculationStatus.VALID
    warnings: tuple[CalculationWarning, ...] = ()

    def __post_init__(self) -> None:
        """Validate the completed load calculation result."""

        normalized_code = self.load_code.strip()
        normalized_name = self.load_name.strip()

        if not normalized_code:
            raise ValueError("load_code must not be empty")

        if not normalized_name:
            raise ValueError("load_name must not be empty")

        if not isinstance(self.scenario, LoadScenario):
            raise TypeError("scenario must be a LoadScenario value")

        if not isinstance(self.phase_system, PhaseSystem):
            raise TypeError("phase_system must be a PhaseSystem value")

        decimal_fields = {
            "connected_power_kw": self.connected_power_kw,
            "utilized_power_kw": self.utilized_power_kw,
            "demand_power_kw": self.demand_power_kw,
            "apparent_power_kva": self.apparent_power_kva,
            "reactive_power_kvar": self.reactive_power_kvar,
            "design_current_a": self.design_current_a,
        }

        for field_name, value in decimal_fields.items():
            _require_non_negative_decimal(
                field_name,
                value,
            )

        if not isinstance(self.status, CalculationStatus):
            raise TypeError("status must be a CalculationStatus value")

        if not all(isinstance(warning, CalculationWarning) for warning in self.warnings):
            raise TypeError("warnings must contain CalculationWarning records")

        _require_status_matches_warnings(
            self.status,
            self.warnings,
        )

        object.__setattr__(
            self,
            "load_code",
            normalized_code,
        )
        object.__setattr__(
            self,
            "load_name",
            normalized_name,
        )


@dataclass(frozen=True, slots=True)
class LoadGroupCalculationResult:
    """Aggregated calculated values for one load group."""

    group_code: str
    group_name: str
    coincidence_factor: Decimal
    connected_power_kw: Decimal
    pre_coincidence_demand_kw: Decimal
    demand_power_kw: Decimal
    apparent_power_kva: Decimal
    reactive_power_kvar: Decimal
    load_results: tuple[LoadCalculationResult, ...]
    status: CalculationStatus = CalculationStatus.VALID
    warnings: tuple[CalculationWarning, ...] = ()
    assumptions: tuple[str, ...] = (GROUP_COINCIDENCE_ASSUMPTION,)

    def __post_init__(self) -> None:
        """Validate the completed load-group result."""

        normalized_code = self.group_code.strip()
        normalized_name = self.group_name.strip()

        if not normalized_code:
            raise ValueError("group_code must not be empty")

        if not normalized_name:
            raise ValueError("group_name must not be empty")

        _require_non_negative_decimal(
            "coincidence_factor",
            self.coincidence_factor,
        )

        if self.coincidence_factor > Decimal("1"):
            raise ValueError("coincidence_factor must not be greater than 1")

        decimal_fields = {
            "connected_power_kw": self.connected_power_kw,
            "pre_coincidence_demand_kw": (self.pre_coincidence_demand_kw),
            "demand_power_kw": self.demand_power_kw,
            "apparent_power_kva": self.apparent_power_kva,
            "reactive_power_kvar": self.reactive_power_kvar,
        }

        for field_name, value in decimal_fields.items():
            _require_non_negative_decimal(
                field_name,
                value,
            )

        if not self.load_results:
            raise ValueError("load_results must not be empty")

        if not all(isinstance(result, LoadCalculationResult) for result in self.load_results):
            raise TypeError("load_results must contain LoadCalculationResult records")

        load_codes = [result.load_code for result in self.load_results]

        if len(load_codes) != len(set(load_codes)):
            raise ValueError("load result codes must be unique")

        if not all(
            isinstance(assumption, str) and assumption.strip() for assumption in self.assumptions
        ):
            raise ValueError("assumptions must contain non-empty text")

        if not isinstance(self.status, CalculationStatus):
            raise TypeError("status must be a CalculationStatus value")

        if not all(isinstance(warning, CalculationWarning) for warning in self.warnings):
            raise TypeError("warnings must contain CalculationWarning records")

        _require_status_matches_warnings(
            self.status,
            self.warnings,
        )

        object.__setattr__(
            self,
            "group_code",
            normalized_code,
        )
        object.__setattr__(
            self,
            "group_name",
            normalized_name,
        )


__all__ = [
    "GROUP_COINCIDENCE_ASSUMPTION",
    "NOT_ESTABLISHED_WARNING_CODES",
    "CalculationStatus",
    "CalculationWarning",
    "LoadCalculationResult",
    "LoadGroupCalculationResult",
    "LoadWarningCode",
    "has_not_established_warning",
    "resolve_status",
]
