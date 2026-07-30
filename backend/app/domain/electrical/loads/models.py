"""
Domain models for electrical load and demand calculations.
KESE-S2-M1
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PhaseSystem(StrEnum):
    """Electrical supply configuration for a load."""

    SINGLE_PHASE = "SINGLE_PHASE"
    THREE_PHASE = "THREE_PHASE"
    DC = "DC"


class LoadScenario(StrEnum):
    """Operating scenario assigned to an electrical load."""

    NORMAL = "NORMAL"
    EMERGENCY = "EMERGENCY"
    OUTAGE = "OUTAGE"
    STARTING = "STARTING"
    UPS = "UPS"
    PV = "PV"
    FUTURE = "FUTURE"


class PowerBasis(StrEnum):
    """Meaning of the rated power supplied for the load."""

    ELECTRICAL_INPUT = "ELECTRICAL_INPUT"
    MECHANICAL_OUTPUT = "MECHANICAL_OUTPUT"


def _require_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    """Require an exact finite Decimal value."""

    if not isinstance(value, Decimal):
        raise TypeError(
            f"{field_name} must be a Decimal; "
            "float values are not permitted"
        )

    if not value.is_finite():
        raise ValueError(
            f"{field_name} must be finite"
        )


def _require_positive_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    """Require an exact Decimal value greater than zero."""

    _require_decimal(field_name, value)

    if value <= Decimal("0"):
        raise ValueError(
            f"{field_name} must be greater than zero"
        )


def _require_ratio(
    field_name: str,
    value: Decimal,
    *,
    allow_zero: bool,
) -> None:
    """Validate a Decimal ratio against the permitted range."""

    _require_decimal(field_name, value)

    lower_limit = Decimal("0")

    if allow_zero:
        valid = lower_limit <= value <= Decimal("1")
        expected_range = "between 0 and 1"
    else:
        valid = lower_limit < value <= Decimal("1")
        expected_range = "greater than 0 and not greater than 1"

    if not valid:
        raise ValueError(
            f"{field_name} must be {expected_range}"
        )


@dataclass(frozen=True, slots=True)
class LoadInput:
    """
    Immutable input record for one electrical load.

    rated_power_kw is the rated power of one unit. The total connected
    power is calculated using rated_power_kw multiplied by quantity.
    """

    code: str
    name: str
    quantity: int
    rated_power_kw: Decimal
    phase_system: PhaseSystem
    voltage_v: Decimal
    power_factor: Decimal = Decimal("1")
    efficiency: Decimal = Decimal("1")
    utilization_factor: Decimal = Decimal("1")
    demand_factor: Decimal = Decimal("1")
    scenario: LoadScenario = LoadScenario.NORMAL
    power_basis: PowerBasis = PowerBasis.ELECTRICAL_INPUT
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the immutable load record."""

        normalized_code = self.code.strip()
        normalized_name = self.name.strip()

        if not normalized_code:
            raise ValueError("code must not be empty")

        if not normalized_name:
            raise ValueError("name must not be empty")

        if isinstance(self.quantity, bool) or not isinstance(
            self.quantity,
            int,
        ):
            raise TypeError("quantity must be an integer")

        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        if not isinstance(self.phase_system, PhaseSystem):
            raise TypeError(
                "phase_system must be a PhaseSystem value"
            )

        if not isinstance(self.scenario, LoadScenario):
            raise TypeError(
                "scenario must be a LoadScenario value"
            )

        if not isinstance(self.power_basis, PowerBasis):
            raise TypeError(
                "power_basis must be a PowerBasis value"
            )

        _require_positive_decimal(
            "rated_power_kw",
            self.rated_power_kw,
        )
        _require_positive_decimal(
            "voltage_v",
            self.voltage_v,
        )
        _require_ratio(
            "power_factor",
            self.power_factor,
            allow_zero=False,
        )
        _require_ratio(
            "efficiency",
            self.efficiency,
            allow_zero=False,
        )
        _require_ratio(
            "utilization_factor",
            self.utilization_factor,
            allow_zero=True,
        )
        _require_ratio(
            "demand_factor",
            self.demand_factor,
            allow_zero=True,
        )

        if (
            self.phase_system is PhaseSystem.DC
            and self.power_factor != Decimal("1")
        ):
            raise ValueError(
                "DC loads must use a power_factor of 1"
            )

        normalized_notes = (
            self.notes.strip()
            if self.notes is not None
            else None
        )

        object.__setattr__(self, "code", normalized_code)
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "notes", normalized_notes)


@dataclass(frozen=True, slots=True)
class LoadGroupInput:
    """
    Immutable group of electrical loads.

    coincidence_factor is applied when the group demand is aggregated.
    """

    code: str
    name: str
    loads: tuple[LoadInput, ...]
    coincidence_factor: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        """Validate the load group and its coincidence factor."""

        normalized_code = self.code.strip()
        normalized_name = self.name.strip()

        if not normalized_code:
            raise ValueError("group code must not be empty")

        if not normalized_name:
            raise ValueError("group name must not be empty")

        if not self.loads:
            raise ValueError(
                "a load group must contain at least one load"
            )

        if not all(
            isinstance(load, LoadInput)
            for load in self.loads
        ):
            raise TypeError(
                "loads must contain only LoadInput records"
            )

        load_codes = [
            load.code
            for load in self.loads
        ]

        if len(load_codes) != len(set(load_codes)):
            raise ValueError(
                "load codes must be unique within a group"
            )

        _require_ratio(
            "coincidence_factor",
            self.coincidence_factor,
            allow_zero=True,
        )

        object.__setattr__(self, "code", normalized_code)
        object.__setattr__(self, "name", normalized_name)


__all__ = [
    "LoadGroupInput",
    "LoadInput",
    "LoadScenario",
    "PhaseSystem",
    "PowerBasis",
]