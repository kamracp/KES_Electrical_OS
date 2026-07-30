"""
Domain models for electrical source and transformer sizing.
KESE-S2-M4
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.loads.models import LoadScenario


class TransformerRedundancyMode(StrEnum):
    """Transformer installation redundancy arrangement."""

    NONE = "NONE"
    N_PLUS_1 = "N_PLUS_1"
    TWO_N = "TWO_N"


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
    """Require a Decimal value greater than zero."""

    _require_decimal(field_name, value)

    if value <= Decimal("0"):
        raise ValueError(
            f"{field_name} must be greater than zero"
        )


def _require_ratio(
    field_name: str,
    value: Decimal,
) -> None:
    """Require a ratio greater than zero and not above one."""

    _require_decimal(field_name, value)

    if not Decimal("0") < value <= Decimal("1"):
        raise ValueError(
            f"{field_name} must be greater than 0 "
            "and not greater than 1"
        )


def _require_factor_not_below_one(
    field_name: str,
    value: Decimal,
) -> None:
    """Require an engineering factor equal to or above one."""

    _require_decimal(field_name, value)

    if value < Decimal("1"):
        raise ValueError(
            f"{field_name} must not be less than 1"
        )


def _normalize_required_text(
    field_name: str,
    value: str,
) -> str:
    """Validate and normalize required text."""

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string"
        )

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(
            f"{field_name} must not be empty"
        )

    return normalized_value


def _normalize_optional_text(
    field_name: str,
    value: str | None,
) -> str | None:
    """Validate and normalize optional text."""

    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string or None"
        )

    normalized_value = value.strip()

    return normalized_value or None


@dataclass(frozen=True, slots=True)
class TransformerSizingInput:
    """
    Immutable transformer-sizing input record.

    available_unit_ratings_kva must come from the controlled project
    design basis, approved standard schedule or manufacturer-neutral
    equipment rating schedule.
    """

    code: str
    name: str

    demand_power_kw: Decimal
    demand_power_factor: Decimal

    available_unit_ratings_kva: tuple[Decimal, ...]

    future_growth_factor: Decimal = Decimal("1")
    design_margin_factor: Decimal = Decimal("1.10")

    ambient_derating_factor: Decimal = Decimal("1")
    altitude_derating_factor: Decimal = Decimal("1")
    harmonic_derating_factor: Decimal = Decimal("1")

    duty_units: int = 1
    standby_units: int = 0

    redundancy_mode: TransformerRedundancyMode = (
        TransformerRedundancyMode.NONE
    )

    scenario: LoadScenario = LoadScenario.NORMAL

    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize transformer-sizing inputs."""

        normalized_code = _normalize_required_text(
            "code",
            self.code,
        )
        normalized_name = _normalize_required_text(
            "name",
            self.name,
        )
        normalized_notes = _normalize_optional_text(
            "notes",
            self.notes,
        )

        _require_positive_decimal(
            "demand_power_kw",
            self.demand_power_kw,
        )

        _require_ratio(
            "demand_power_factor",
            self.demand_power_factor,
        )

        _require_factor_not_below_one(
            "future_growth_factor",
            self.future_growth_factor,
        )

        _require_factor_not_below_one(
            "design_margin_factor",
            self.design_margin_factor,
        )

        _require_ratio(
            "ambient_derating_factor",
            self.ambient_derating_factor,
        )

        _require_ratio(
            "altitude_derating_factor",
            self.altitude_derating_factor,
        )

        _require_ratio(
            "harmonic_derating_factor",
            self.harmonic_derating_factor,
        )

        if (
            isinstance(self.duty_units, bool)
            or not isinstance(self.duty_units, int)
        ):
            raise TypeError(
                "duty_units must be an integer"
            )

        if self.duty_units <= 0:
            raise ValueError(
                "duty_units must be greater than zero"
            )

        if (
            isinstance(self.standby_units, bool)
            or not isinstance(self.standby_units, int)
        ):
            raise TypeError(
                "standby_units must be an integer"
            )

        if self.standby_units < 0:
            raise ValueError(
                "standby_units must not be negative"
            )

        if not isinstance(
            self.redundancy_mode,
            TransformerRedundancyMode,
        ):
            raise TypeError(
                "redundancy_mode must be a "
                "TransformerRedundancyMode value"
            )

        if not isinstance(
            self.scenario,
            LoadScenario,
        ):
            raise TypeError(
                "scenario must be a LoadScenario value"
            )

        if not isinstance(
            self.available_unit_ratings_kva,
            tuple,
        ):
            raise TypeError(
                "available_unit_ratings_kva must be a tuple"
            )

        if not self.available_unit_ratings_kva:
            raise ValueError(
                "at least one available transformer "
                "rating is required"
            )

        for rating in self.available_unit_ratings_kva:
            _require_positive_decimal(
                "available_unit_ratings_kva rating",
                rating,
            )

        if len(
            self.available_unit_ratings_kva
        ) != len(set(self.available_unit_ratings_kva)):
            raise ValueError(
                "available transformer ratings "
                "must be unique"
            )

        if self.available_unit_ratings_kva != tuple(
            sorted(self.available_unit_ratings_kva)
        ):
            raise ValueError(
                "available transformer ratings "
                "must be in ascending order"
            )

        if (
            self.redundancy_mode
            is TransformerRedundancyMode.NONE
            and self.standby_units != 0
        ):
            raise ValueError(
                "NONE redundancy requires "
                "standby_units to be 0"
            )

        if (
            self.redundancy_mode
            is TransformerRedundancyMode.N_PLUS_1
            and self.standby_units != 1
        ):
            raise ValueError(
                "N_PLUS_1 redundancy requires "
                "exactly one standby unit"
            )

        if (
            self.redundancy_mode
            is TransformerRedundancyMode.TWO_N
            and self.standby_units != self.duty_units
        ):
            raise ValueError(
                "TWO_N redundancy requires standby_units "
                "to equal duty_units"
            )

        object.__setattr__(
            self,
            "code",
            normalized_code,
        )
        object.__setattr__(
            self,
            "name",
            normalized_name,
        )
        object.__setattr__(
            self,
            "notes",
            normalized_notes,
        )


__all__ = [
    "TransformerRedundancyMode",
    "TransformerSizingInput",
]
