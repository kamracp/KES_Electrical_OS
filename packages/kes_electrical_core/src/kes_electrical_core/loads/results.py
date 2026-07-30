"""
Result models for electrical load and demand calculations.
KESE-S2-M1
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from kes_electrical_core.loads.models import (
    LoadScenario,
    PhaseSystem,
)


class CalculationStatus(StrEnum):
    """Overall state of a completed calculation."""

    VALID = "VALID"
    WARNING = "WARNING"


class LoadWarningCode(StrEnum):
    """Controlled warnings produced by load calculations."""

    ZERO_DEMAND = "ZERO_DEMAND"
    LOW_POWER_FACTOR = "LOW_POWER_FACTOR"
    LOW_EFFICIENCY = "LOW_EFFICIENCY"


@dataclass(frozen=True, slots=True)
class CalculationWarning:
    """Structured engineering calculation warning."""

    code: LoadWarningCode
    message: str

    def __post_init__(self) -> None:
        """Validate warning content."""

        if not isinstance(self.code, LoadWarningCode):
            raise TypeError(
                "code must be a LoadWarningCode value"
            )

        normalized_message = self.message.strip()

        if not normalized_message:
            raise ValueError(
                "warning message must not be empty"
            )

        object.__setattr__(
            self,
            "message",
            normalized_message,
        )


def _require_non_negative_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    """Require an exact, finite, non-negative Decimal."""

    if not isinstance(value, Decimal):
        raise TypeError(
            f"{field_name} must be a Decimal"
        )

    if not value.is_finite():
        raise ValueError(
            f"{field_name} must be finite"
        )

    if value < Decimal("0"):
        raise ValueError(
            f"{field_name} must not be negative"
        )


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
            raise ValueError(
                "load_code must not be empty"
            )

        if not normalized_name:
            raise ValueError(
                "load_name must not be empty"
            )

        if not isinstance(self.scenario, LoadScenario):
            raise TypeError(
                "scenario must be a LoadScenario value"
            )

        if not isinstance(self.phase_system, PhaseSystem):
            raise TypeError(
                "phase_system must be a PhaseSystem value"
            )

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
            raise TypeError(
                "status must be a CalculationStatus value"
            )

        if not all(
            isinstance(warning, CalculationWarning)
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain CalculationWarning records"
            )

        if (
            self.status is CalculationStatus.VALID
            and self.warnings
        ):
            raise ValueError(
                "VALID result must not contain warnings"
            )

        if (
            self.status is CalculationStatus.WARNING
            and not self.warnings
        ):
            raise ValueError(
                "WARNING result must contain at least one warning"
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

    def __post_init__(self) -> None:
        """Validate the completed load-group result."""

        normalized_code = self.group_code.strip()
        normalized_name = self.group_name.strip()

        if not normalized_code:
            raise ValueError(
                "group_code must not be empty"
            )

        if not normalized_name:
            raise ValueError(
                "group_name must not be empty"
            )

        _require_non_negative_decimal(
            "coincidence_factor",
            self.coincidence_factor,
        )

        if self.coincidence_factor > Decimal("1"):
            raise ValueError(
                "coincidence_factor must not be greater than 1"
            )

        decimal_fields = {
            "connected_power_kw": self.connected_power_kw,
            "pre_coincidence_demand_kw": (
                self.pre_coincidence_demand_kw
            ),
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
            raise ValueError(
                "load_results must not be empty"
            )

        if not all(
            isinstance(result, LoadCalculationResult)
            for result in self.load_results
        ):
            raise TypeError(
                "load_results must contain "
                "LoadCalculationResult records"
            )

        load_codes = [
            result.load_code
            for result in self.load_results
        ]

        if len(load_codes) != len(set(load_codes)):
            raise ValueError(
                "load result codes must be unique"
            )

        if not isinstance(self.status, CalculationStatus):
            raise TypeError(
                "status must be a CalculationStatus value"
            )

        if not all(
            isinstance(warning, CalculationWarning)
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain CalculationWarning records"
            )

        if (
            self.status is CalculationStatus.VALID
            and self.warnings
        ):
            raise ValueError(
                "VALID result must not contain warnings"
            )

        if (
            self.status is CalculationStatus.WARNING
            and not self.warnings
        ):
            raise ValueError(
                "WARNING result must contain at least one warning"
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
    "CalculationStatus",
    "CalculationWarning",
    "LoadCalculationResult",
    "LoadGroupCalculationResult",
    "LoadWarningCode",
]