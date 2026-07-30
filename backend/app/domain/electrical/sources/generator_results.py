"""
Result models for generator source sizing.
KESE-S2-M6
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.generator_models import (
    GeneratorDutyClass,
    GeneratorRedundancyMode,
)


class GeneratorSizingStatus(StrEnum):
    """Engineering status of a generator-sizing result."""

    VALID = "VALID"
    WARNING = "WARNING"
    NO_SOLUTION = "NO_SOLUTION"


class GeneratorSizingWarningCode(StrEnum):
    """Controlled generator-sizing warning codes."""

    DERATING_APPLIED = "DERATING_APPLIED"
    TRANSIENT_REQUIREMENT_GOVERNS = (
        "TRANSIENT_REQUIREMENT_GOVERNS"
    )
    HIGH_LOADING = "HIGH_LOADING"
    LOW_LOADING = "LOW_LOADING"
    NO_STANDARD_RATING_AVAILABLE = (
        "NO_STANDARD_RATING_AVAILABLE"
    )


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


@dataclass(frozen=True, slots=True)
class GeneratorSizingWarning:
    """Structured engineering warning for generator sizing."""

    code: GeneratorSizingWarningCode
    message: str

    def __post_init__(self) -> None:
        """Validate and normalize warning details."""

        if not isinstance(
            self.code,
            GeneratorSizingWarningCode,
        ):
            raise TypeError(
                "code must be a "
                "GeneratorSizingWarningCode value"
            )

        normalized_message = _normalize_required_text(
            "warning message",
            self.message,
        )

        object.__setattr__(
            self,
            "message",
            normalized_message,
        )


@dataclass(frozen=True, slots=True)
class GeneratorSizingResult:
    """
    Immutable engineering result for generator source sizing.

    steady_state_required_kva represents the running-load capacity
    requirement after future growth and design margin.

    transient_required_kva represents the future running demand plus
    the controlled transient or starting-load allowance.

    governing_required_kva is the larger of the steady-state and
    transient requirements.

    A NO_SOLUTION result has no selected generator rating.
    """

    code: str
    name: str

    scenario: LoadScenario
    duty_class: GeneratorDutyClass
    redundancy_mode: GeneratorRedundancyMode

    steady_state_demand_kw: Decimal
    steady_state_power_factor: Decimal
    steady_state_demand_kva: Decimal

    future_growth_factor: Decimal
    future_steady_state_kva: Decimal

    design_margin_factor: Decimal
    steady_state_required_kva: Decimal

    transient_step_load_kva: Decimal
    transient_allowance_factor: Decimal
    transient_additional_kva: Decimal
    transient_required_kva: Decimal

    governing_required_kva: Decimal

    combined_derating_factor: Decimal
    required_nameplate_capacity_kva: Decimal

    duty_units: int
    standby_units: int
    total_units: int

    required_unit_rating_kva: Decimal
    selected_unit_rating_kva: Decimal | None

    installed_nameplate_capacity_kva: Decimal | None
    derated_duty_capacity_kva: Decimal | None
    spare_derated_capacity_kva: Decimal | None
    steady_state_loading_percent: Decimal | None

    status: GeneratorSizingStatus

    warnings: tuple[GeneratorSizingWarning, ...]

    def __post_init__(self) -> None:
        """Validate result consistency and normalize identifiers."""

        normalized_code = _normalize_required_text(
            "code",
            self.code,
        )
        normalized_name = _normalize_required_text(
            "name",
            self.name,
        )

        if not isinstance(
            self.scenario,
            LoadScenario,
        ):
            raise TypeError(
                "scenario must be a LoadScenario value"
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
            self.status,
            GeneratorSizingStatus,
        ):
            raise TypeError(
                "status must be a GeneratorSizingStatus value"
            )

        for field_name, value in {
            "steady_state_demand_kw": (
                self.steady_state_demand_kw
            ),
            "steady_state_demand_kva": (
                self.steady_state_demand_kva
            ),
            "future_steady_state_kva": (
                self.future_steady_state_kva
            ),
            "steady_state_required_kva": (
                self.steady_state_required_kva
            ),
            "transient_required_kva": (
                self.transient_required_kva
            ),
            "governing_required_kva": (
                self.governing_required_kva
            ),
            "required_nameplate_capacity_kva": (
                self.required_nameplate_capacity_kva
            ),
            "required_unit_rating_kva": (
                self.required_unit_rating_kva
            ),
        }.items():
            _require_positive_decimal(
                field_name,
                value,
            )

        _require_ratio(
            "steady_state_power_factor",
            self.steady_state_power_factor,
        )
        _require_factor_not_below_one(
            "future_growth_factor",
            self.future_growth_factor,
        )
        _require_factor_not_below_one(
            "design_margin_factor",
            self.design_margin_factor,
        )
        _require_non_negative_decimal(
            "transient_step_load_kva",
            self.transient_step_load_kva,
        )
        _require_factor_not_below_one(
            "transient_allowance_factor",
            self.transient_allowance_factor,
        )
        _require_non_negative_decimal(
            "transient_additional_kva",
            self.transient_additional_kva,
        )
        _require_ratio(
            "combined_derating_factor",
            self.combined_derating_factor,
        )

        if self.governing_required_kva < (
            self.steady_state_required_kva
        ):
            raise ValueError(
                "governing_required_kva must not be below "
                "steady_state_required_kva"
            )

        if self.governing_required_kva < (
            self.transient_required_kva
        ):
            raise ValueError(
                "governing_required_kva must not be below "
                "transient_required_kva"
            )

        for field_name, value in {
            "duty_units": self.duty_units,
            "standby_units": self.standby_units,
            "total_units": self.total_units,
        }.items():
            if isinstance(value, bool) or not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{field_name} must be an integer"
                )

        if self.duty_units <= 0:
            raise ValueError(
                "duty_units must be greater than zero"
            )

        if self.standby_units < 0:
            raise ValueError(
                "standby_units must not be negative"
            )

        if self.total_units != (
            self.duty_units + self.standby_units
        ):
            raise ValueError(
                "total_units must equal duty_units "
                "plus standby_units"
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

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        if not all(
            isinstance(
                warning,
                GeneratorSizingWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only "
                "GeneratorSizingWarning records"
            )

        warning_codes = tuple(
            warning.code
            for warning in self.warnings
        )

        if len(warning_codes) != len(set(warning_codes)):
            raise ValueError(
                "warning codes must be unique"
            )

        optional_capacity_fields = {
            "installed_nameplate_capacity_kva": (
                self.installed_nameplate_capacity_kva
            ),
            "derated_duty_capacity_kva": (
                self.derated_duty_capacity_kva
            ),
            "spare_derated_capacity_kva": (
                self.spare_derated_capacity_kva
            ),
            "steady_state_loading_percent": (
                self.steady_state_loading_percent
            ),
        }

        if self.selected_unit_rating_kva is None:
            if (
                self.status
                is not GeneratorSizingStatus.NO_SOLUTION
            ):
                raise ValueError(
                    "missing selected rating requires "
                    "NO_SOLUTION status"
                )

            if any(
                value is not None
                for value in optional_capacity_fields.values()
            ):
                raise ValueError(
                    "capacity and loading results must be "
                    "None when no rating is selected"
                )

            if (
                GeneratorSizingWarningCode
                .NO_STANDARD_RATING_AVAILABLE
                not in warning_codes
            ):
                raise ValueError(
                    "NO_SOLUTION result requires "
                    "NO_STANDARD_RATING_AVAILABLE warning"
                )
        else:
            _require_positive_decimal(
                "selected_unit_rating_kva",
                self.selected_unit_rating_kva,
            )

            if (
                self.status
                is GeneratorSizingStatus.NO_SOLUTION
            ):
                raise ValueError(
                    "NO_SOLUTION status cannot contain "
                    "a selected rating"
                )

            if any(
                value is None
                for value in optional_capacity_fields.values()
            ):
                raise ValueError(
                    "selected rating requires complete "
                    "capacity and loading results"
                )

            for field_name, value in (
                optional_capacity_fields.items()
            ):
                assert value is not None

                _require_non_negative_decimal(
                    field_name,
                    value,
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


__all__ = [
    "GeneratorSizingResult",
    "GeneratorSizingStatus",
    "GeneratorSizingWarning",
    "GeneratorSizingWarningCode",
]
