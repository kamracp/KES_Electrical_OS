"""
Result models for electrical source and transformer sizing.
KESE-S2-M4
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.models import (
    TransformerRedundancyMode,
)


class TransformerSizingStatus(StrEnum):
    """Engineering status of a transformer-sizing result."""

    VALID = "VALID"
    WARNING = "WARNING"
    NO_SOLUTION = "NO_SOLUTION"


class TransformerSizingWarningCode(StrEnum):
    """Controlled transformer-sizing warning codes."""

    DERATING_APPLIED = "DERATING_APPLIED"
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
class TransformerSizingWarning:
    """Structured engineering warning for transformer sizing."""

    code: TransformerSizingWarningCode
    message: str

    def __post_init__(self) -> None:
        """Validate and normalize warning details."""

        if not isinstance(
            self.code,
            TransformerSizingWarningCode,
        ):
            raise TypeError(
                "code must be a "
                "TransformerSizingWarningCode value"
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
class TransformerSizingResult:
    """
    Immutable engineering result for transformer source sizing.

    Capacity values represent manufacturer-neutral nameplate and
    derated capacities. A NO_SOLUTION result has no selected rating.
    """

    code: str
    name: str

    scenario: LoadScenario
    redundancy_mode: TransformerRedundancyMode

    demand_power_kw: Decimal
    demand_power_factor: Decimal
    base_demand_kva: Decimal

    future_growth_factor: Decimal
    future_demand_kva: Decimal

    design_margin_factor: Decimal
    design_required_kva: Decimal

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
    loading_percent: Decimal | None

    status: TransformerSizingStatus

    warnings: tuple[TransformerSizingWarning, ...]

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
            self.redundancy_mode,
            TransformerRedundancyMode,
        ):
            raise TypeError(
                "redundancy_mode must be a "
                "TransformerRedundancyMode value"
            )

        if not isinstance(
            self.status,
            TransformerSizingStatus,
        ):
            raise TypeError(
                "status must be a "
                "TransformerSizingStatus value"
            )

        for field_name, value in {
            "demand_power_kw": self.demand_power_kw,
            "base_demand_kva": self.base_demand_kva,
            "future_demand_kva": self.future_demand_kva,
            "design_required_kva": self.design_required_kva,
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
            "combined_derating_factor",
            self.combined_derating_factor,
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

        if not isinstance(self.warnings, tuple):
            raise TypeError(
                "warnings must be a tuple"
            )

        if not all(
            isinstance(
                warning,
                TransformerSizingWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only "
                "TransformerSizingWarning records"
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
            "loading_percent": self.loading_percent,
        }

        if self.selected_unit_rating_kva is None:
            if (
                self.status
                is not TransformerSizingStatus.NO_SOLUTION
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
                TransformerSizingWarningCode
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
                is TransformerSizingStatus.NO_SOLUTION
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
    "TransformerSizingResult",
    "TransformerSizingStatus",
    "TransformerSizingWarning",
    "TransformerSizingWarningCode",
]
