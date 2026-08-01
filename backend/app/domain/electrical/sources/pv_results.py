"""
Result models for Solar PV source sizing.
KESE-S2-M8
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.pv_models import (
    PVBatteryConfiguration,
    PVInverterRedundancyMode,
    PVPhaseConfiguration,
    PVSystemType,
)


class PVSizingStatus(StrEnum):
    """Solar PV sizing result status."""

    VALID = "VALID"
    WARNING = "WARNING"
    NO_SOLUTION = "NO_SOLUTION"


class PVSizingWarningCode(StrEnum):
    """Structured Solar PV engineering warning codes."""

    COLD_VOC_LIMIT = "COLD_VOC_LIMIT"
    HOT_VMP_BELOW_MPPT = "HOT_VMP_BELOW_MPPT"
    STRING_CURRENT_LIMIT = "STRING_CURRENT_LIMIT"
    HIGH_DC_AC_RATIO = "HIGH_DC_AC_RATIO"
    LOW_DC_AC_RATIO = "LOW_DC_AC_RATIO"
    EXPORT_LIMIT_APPLIED = "EXPORT_LIMIT_APPLIED"
    DG_COORDINATION_REQUIRED = "DG_COORDINATION_REQUIRED"
    NO_STANDARD_INVERTER_RATING = (
        "NO_STANDARD_INVERTER_RATING"
    )


def _require_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(
            f"{field_name} must be a Decimal"
        )

    if not value.is_finite():
        raise ValueError(
            f"{field_name} must be finite"
        )


def _require_non_negative_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    _require_decimal(field_name, value)

    if value < Decimal("0"):
        raise ValueError(
            f"{field_name} must not be negative"
        )


def _normalize_required_text(
    field_name: str,
    value: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} must not be empty"
        )

    return normalized


@dataclass(frozen=True, slots=True)
class PVSizingWarning:
    """Structured Solar PV engineering warning."""

    code: PVSizingWarningCode
    message: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.code,
            PVSizingWarningCode,
        ):
            raise TypeError(
                "code must be a PVSizingWarningCode value"
            )

        object.__setattr__(
            self,
            "message",
            _normalize_required_text(
                "message",
                self.message,
            ),
        )


@dataclass(frozen=True, slots=True)
class PVSizingResult:
    """Immutable Solar PV source-sizing result."""

    code: str
    name: str

    scenario: LoadScenario
    system_type: PVSystemType
    phase_configuration: PVPhaseConfiguration
    redundancy_mode: PVInverterRedundancyMode
    battery_configuration: PVBatteryConfiguration

    required_ac_output_kw: Decimal
    future_required_ac_output_kw: Decimal
    design_required_ac_output_kw: Decimal

    target_dc_ac_ratio: Decimal
    required_dc_array_capacity_kwp: Decimal

    module_rated_power_wp: Decimal
    total_modules: int

    modules_per_string: int
    total_strings: int
    strings_per_mppt: int

    cold_corrected_module_voc_v: Decimal
    hot_corrected_module_vmp_v: Decimal

    cold_string_voc_v: Decimal
    hot_string_vmp_v: Decimal
    string_short_circuit_current_a: Decimal

    required_inverter_capacity_kw: Decimal
    required_unit_rating_kw: Decimal
    selected_unit_rating_kw: Decimal | None

    duty_inverters: int
    redundant_inverters: int
    total_inverters: int

    installed_duty_capacity_kw: Decimal | None
    total_installed_capacity_kw: Decimal | None
    actual_dc_ac_ratio: Decimal | None
    spare_ac_capacity_kw: Decimal | None

    export_limit_kw: Decimal | None
    dg_coexistence: bool

    status: PVSizingStatus
    warnings: tuple[PVSizingWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            _normalize_required_text(
                "code",
                self.code,
            ),
        )
        object.__setattr__(
            self,
            "name",
            _normalize_required_text(
                "name",
                self.name,
            ),
        )

        for field_name, value in {
            "required_ac_output_kw": (
                self.required_ac_output_kw
            ),
            "future_required_ac_output_kw": (
                self.future_required_ac_output_kw
            ),
            "design_required_ac_output_kw": (
                self.design_required_ac_output_kw
            ),
            "required_dc_array_capacity_kwp": (
                self.required_dc_array_capacity_kwp
            ),
            "required_inverter_capacity_kw": (
                self.required_inverter_capacity_kw
            ),
            "required_unit_rating_kw": (
                self.required_unit_rating_kw
            ),
        }.items():
            _require_non_negative_decimal(
                field_name,
                value,
            )

        for field_name, value in {
            "total_modules": self.total_modules,
            "modules_per_string": self.modules_per_string,
            "total_strings": self.total_strings,
            "strings_per_mppt": self.strings_per_mppt,
            "duty_inverters": self.duty_inverters,
            "redundant_inverters": (
                self.redundant_inverters
            ),
            "total_inverters": self.total_inverters,
        }.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{field_name} must be an integer"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        if self.total_inverters != (
            self.duty_inverters
            + self.redundant_inverters
        ):
            raise ValueError(
                "total_inverters must equal duty_inverters "
                "plus redundant_inverters"
            )

        if not isinstance(
            self.status,
            PVSizingStatus,
        ):
            raise TypeError(
                "status must be a PVSizingStatus value"
            )

        if not isinstance(self.warnings, tuple):
            raise TypeError(
                "warnings must be a tuple"
            )

        if not all(
            isinstance(warning, PVSizingWarning)
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only "
                "PVSizingWarning records"
            )

        warning_codes = tuple(
            warning.code
            for warning in self.warnings
        )

        if len(warning_codes) != len(set(warning_codes)):
            raise ValueError(
                "warning codes must be unique"
            )

        optional_values = (
            self.selected_unit_rating_kw,
            self.installed_duty_capacity_kw,
            self.total_installed_capacity_kw,
            self.actual_dc_ac_ratio,
            self.spare_ac_capacity_kw,
        )

        if self.status is PVSizingStatus.NO_SOLUTION:
            if any(
                value is not None
                for value in optional_values
            ):
                raise ValueError(
                    "NO_SOLUTION result must not contain "
                    "selected capacity values"
                )
        elif any(
            value is None
            for value in optional_values
        ):
            raise ValueError(
                "selected PV result requires complete "
                "capacity values"
            )


__all__ = [
    "PVSizingResult",
    "PVSizingStatus",
    "PVSizingWarning",
    "PVSizingWarningCode",
]
