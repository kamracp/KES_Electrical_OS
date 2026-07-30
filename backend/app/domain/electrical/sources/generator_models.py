"""
Domain input models for generator source sizing.
KESE-S2-M6
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.loads.models import LoadScenario


class GeneratorDutyClass(StrEnum):
    """Declared generator operating-duty classification."""

    STANDBY = "STANDBY"
    PRIME = "PRIME"
    CONTINUOUS = "CONTINUOUS"


class GeneratorRedundancyMode(StrEnum):
    """Generator installation redundancy arrangement."""

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
    """Require an exact Decimal value greater than zero."""

    _require_decimal(field_name, value)

    if value <= Decimal("0"):
        raise ValueError(
            f"{field_name} must be greater than zero"
        )


def _require_non_negative_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    """Require an exact Decimal value equal to or above zero."""

    _require_decimal(field_name, value)

    if value < Decimal("0"):
        raise ValueError(
            f"{field_name} must not be negative"
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
class GeneratorSizingInput:
    """
    Immutable generator source-sizing input record.

    steady_state_demand_kw represents the simultaneous running demand.

    transient_step_load_kva represents the additional short-duration
    starting or block-load requirement. It must come from a controlled
    motor-starting study, approved design basis or documented assumption.

    available_unit_ratings_kva must be an ascending, unique and
    manufacturer-neutral standard-rating schedule.
    """

    code: str
    name: str

    steady_state_demand_kw: Decimal
    steady_state_power_factor: Decimal

    transient_step_load_kva: Decimal = Decimal("0")
    transient_allowance_factor: Decimal = Decimal("1")

    future_growth_factor: Decimal = Decimal("1")
    design_margin_factor: Decimal = Decimal("1.10")

    ambient_derating_factor: Decimal = Decimal("1")
    altitude_derating_factor: Decimal = Decimal("1")

    available_unit_ratings_kva: tuple[Decimal, ...] = ()

    duty_units: int = 1
    standby_units: int = 0

    duty_class: GeneratorDutyClass = GeneratorDutyClass.STANDBY

    redundancy_mode: GeneratorRedundancyMode = (
        GeneratorRedundancyMode.NONE
    )

    scenario: LoadScenario = LoadScenario.EMERGENCY

    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize generator-sizing inputs."""

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
            "steady_state_demand_kw",
            self.steady_state_demand_kw,
        )
        _require_ratio(
            "steady_state_power_factor",
            self.steady_state_power_factor,
        )
        _require_non_negative_decimal(
            "transient_step_load_kva",
            self.transient_step_load_kva,
        )
        _require_factor_not_below_one(
            "transient_allowance_factor",
            self.transient_allowance_factor,
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
            self.duty_class,
            GeneratorDutyClass,
        ):
            raise TypeError(
                "duty_class must be a GeneratorDutyClass value"
            )

        if not isinstance(
            self.redundancy_mode,
            GeneratorRedundancyMode,
        ):
            raise TypeError(
                "redundancy_mode must be a "
                "GeneratorRedundancyMode value"
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
                "at least one available generator "
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
                "available generator ratings must be unique"
            )

        if self.available_unit_ratings_kva != tuple(
            sorted(self.available_unit_ratings_kva)
        ):
            raise ValueError(
                "available generator ratings "
                "must be in ascending order"
            )

        if (
            self.redundancy_mode
            is GeneratorRedundancyMode.NONE
            and self.standby_units != 0
        ):
            raise ValueError(
                "NONE redundancy requires "
                "standby_units to be 0"
            )

        if (
            self.redundancy_mode
            is GeneratorRedundancyMode.N_PLUS_1
            and self.standby_units != 1
        ):
            raise ValueError(
                "N_PLUS_1 redundancy requires "
                "exactly one standby unit"
            )

        if (
            self.redundancy_mode
            is GeneratorRedundancyMode.TWO_N
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
    "GeneratorDutyClass",
    "GeneratorRedundancyMode",
    "GeneratorSizingInput",
]
