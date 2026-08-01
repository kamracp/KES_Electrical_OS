"""
Domain input models for Solar PV source sizing.
KESE-S2-M8
"""


from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.loads.models import LoadScenario


class PVSystemType(StrEnum):
    """Solar PV operating configuration."""

    GRID_TIED = "GRID_TIED"
    HYBRID = "HYBRID"
    OFF_GRID = "OFF_GRID"


class PVPhaseConfiguration(StrEnum):
    """PV inverter AC phase configuration."""

    SINGLE_PHASE = "SINGLE_PHASE"
    THREE_PHASE = "THREE_PHASE"


class PVInverterRedundancyMode(StrEnum):
    """PV inverter redundancy arrangement."""

    NONE = "NONE"
    N_PLUS_1 = "N_PLUS_1"
    TWO_N = "TWO_N"


class PVBatteryConfiguration(StrEnum):
    """Battery integration arrangement."""

    NONE = "NONE"
    DC_COUPLED = "DC_COUPLED"
    AC_COUPLED = "AC_COUPLED"


def _require_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(
            f"{field_name} must be a Decimal; "
            "float values are not permitted"
        )

    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite")


def _require_positive_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    _require_decimal(field_name, value)

    if value <= Decimal("0"):
        raise ValueError(
            f"{field_name} must be greater than zero"
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


def _require_ratio(
    field_name: str,
    value: Decimal,
) -> None:
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
    _require_decimal(field_name, value)

    if value < Decimal("1"):
        raise ValueError(
            f"{field_name} must not be less than 1"
        )


def _require_non_positive_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    _require_decimal(field_name, value)

    if value > Decimal("0"):
        raise ValueError(
            f"{field_name} must not be positive"
        )


def _normalize_required_text(
    field_name: str,
    value: str,
) -> str:
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
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string or None"
        )

    return value.strip() or None


@dataclass(frozen=True, slots=True)
class PVSizingInput:
   

    code: str
    name: str

    required_ac_output_kw: Decimal

    module_rated_power_wp: Decimal
    module_open_circuit_voltage_v: Decimal
    module_maximum_power_voltage_v: Decimal
    module_short_circuit_current_a: Decimal
    module_maximum_power_current_a: Decimal

    temperature_coefficient_voc_percent_per_c: Decimal
    temperature_coefficient_vmp_percent_per_c: Decimal

    minimum_design_temperature_c: Decimal
    maximum_cell_temperature_c: Decimal

    inverter_max_dc_voltage_v: Decimal
    inverter_mppt_min_voltage_v: Decimal
    inverter_mppt_max_voltage_v: Decimal
    inverter_max_input_current_per_mppt_a: Decimal

    available_inverter_ratings_kw: tuple[Decimal, ...]

    target_dc_ac_ratio: Decimal = Decimal("1.20")
    design_irradiance_w_per_m2: Decimal = Decimal("1000")

    dc_efficiency_factor: Decimal = Decimal("0.97")
    ac_efficiency_factor: Decimal = Decimal("0.98")

    future_growth_factor: Decimal = Decimal("1")
    design_margin_factor: Decimal = Decimal("1")

    mppt_count: int = 1
    maximum_strings_per_mppt: int = 2

    duty_inverters: int = 1
    redundant_inverters: int = 0

    system_type: PVSystemType = PVSystemType.GRID_TIED
    phase_configuration: PVPhaseConfiguration = (
        PVPhaseConfiguration.THREE_PHASE
    )
    redundancy_mode: PVInverterRedundancyMode = (
        PVInverterRedundancyMode.NONE
    )
    battery_configuration: PVBatteryConfiguration = (
        PVBatteryConfiguration.NONE
    )

    export_limit_kw: Decimal | None = None
    dg_coexistence: bool = False

    scenario: LoadScenario = LoadScenario.PV
    notes: str | None = None

    def __post_init__(self) -> None:
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

        for field_name, value in {
            "required_ac_output_kw": self.required_ac_output_kw,
            "module_rated_power_wp": self.module_rated_power_wp,
            "module_open_circuit_voltage_v": (
                self.module_open_circuit_voltage_v
            ),
            "module_maximum_power_voltage_v": (
                self.module_maximum_power_voltage_v
            ),
            "module_short_circuit_current_a": (
                self.module_short_circuit_current_a
            ),
            "module_maximum_power_current_a": (
                self.module_maximum_power_current_a
            ),
            "inverter_max_dc_voltage_v": (
                self.inverter_max_dc_voltage_v
            ),
            "inverter_mppt_min_voltage_v": (
                self.inverter_mppt_min_voltage_v
            ),
            "inverter_mppt_max_voltage_v": (
                self.inverter_mppt_max_voltage_v
            ),
            "inverter_max_input_current_per_mppt_a": (
                self.inverter_max_input_current_per_mppt_a
            ),
            "target_dc_ac_ratio": self.target_dc_ac_ratio,
            "design_irradiance_w_per_m2": (
                self.design_irradiance_w_per_m2
            ),
        }.items():
            _require_positive_decimal(field_name, value)

        _require_non_positive_decimal(
            "temperature_coefficient_voc_percent_per_c",
            self.temperature_coefficient_voc_percent_per_c,
        )
        _require_non_positive_decimal(
            "temperature_coefficient_vmp_percent_per_c",
            self.temperature_coefficient_vmp_percent_per_c,
        )

        _require_decimal(
            "minimum_design_temperature_c",
            self.minimum_design_temperature_c,
        )
        _require_decimal(
            "maximum_cell_temperature_c",
            self.maximum_cell_temperature_c,
        )

        if (
            self.minimum_design_temperature_c
            >= self.maximum_cell_temperature_c
        ):
            raise ValueError(
                "minimum_design_temperature_c must be below "
                "maximum_cell_temperature_c"
            )

        for field_name, value in {
            "dc_efficiency_factor": self.dc_efficiency_factor,
            "ac_efficiency_factor": self.ac_efficiency_factor,
        }.items():
            _require_ratio(field_name, value)

        _require_factor_not_below_one(
            "future_growth_factor",
            self.future_growth_factor,
        )
        _require_factor_not_below_one(
            "design_margin_factor",
            self.design_margin_factor,
        )

        for field_name, value in {
            "mppt_count": self.mppt_count,
            "maximum_strings_per_mppt": (
                self.maximum_strings_per_mppt
            ),
            "duty_inverters": self.duty_inverters,
            "redundant_inverters": self.redundant_inverters,
        }.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{field_name} must be an integer"
                )

        if self.mppt_count <= 0:
            raise ValueError(
                "mppt_count must be greater than zero"
            )

        if self.maximum_strings_per_mppt <= 0:
            raise ValueError(
                "maximum_strings_per_mppt must be greater than zero"
            )

        if self.duty_inverters <= 0:
            raise ValueError(
                "duty_inverters must be greater than zero"
            )

        if self.redundant_inverters < 0:
            raise ValueError(
                "redundant_inverters must not be negative"
            )

        if not isinstance(
            self.available_inverter_ratings_kw,
            tuple,
        ):
            raise TypeError(
                "available_inverter_ratings_kw must be a tuple"
            )

        if not self.available_inverter_ratings_kw:
            raise ValueError(
                "at least one available inverter rating is required"
            )

        for rating in self.available_inverter_ratings_kw:
            _require_positive_decimal(
                "available_inverter_ratings_kw rating",
                rating,
            )

        if len(
            self.available_inverter_ratings_kw
        ) != len(set(self.available_inverter_ratings_kw)):
            raise ValueError(
                "available inverter ratings must be unique"
            )

        if self.available_inverter_ratings_kw != tuple(
            sorted(self.available_inverter_ratings_kw)
        ):
            raise ValueError(
                "available inverter ratings must be in ascending order"
            )

        if (
            self.inverter_mppt_min_voltage_v
            >= self.inverter_mppt_max_voltage_v
        ):
            raise ValueError(
                "inverter_mppt_min_voltage_v must be below "
                "inverter_mppt_max_voltage_v"
            )

        if (
            self.inverter_mppt_max_voltage_v
            > self.inverter_max_dc_voltage_v
        ):
            raise ValueError(
                "inverter MPPT maximum voltage must not exceed "
                "inverter maximum DC voltage"
            )

        if not isinstance(self.dg_coexistence, bool):
            raise TypeError(
                "dg_coexistence must be a boolean"
            )

        if self.export_limit_kw is not None:
            _require_non_negative_decimal(
                "export_limit_kw",
                self.export_limit_kw,
            )

        if not isinstance(self.system_type, PVSystemType):
            raise TypeError(
                "system_type must be a PVSystemType value"
            )

        if not isinstance(
            self.phase_configuration,
            PVPhaseConfiguration,
        ):
            raise TypeError(
                "phase_configuration must be a "
                "PVPhaseConfiguration value"
            )

        if not isinstance(
            self.redundancy_mode,
            PVInverterRedundancyMode,
        ):
            raise TypeError(
                "redundancy_mode must be a "
                "PVInverterRedundancyMode value"
            )

        if not isinstance(
            self.battery_configuration,
            PVBatteryConfiguration,
        ):
            raise TypeError(
                "battery_configuration must be a "
                "PVBatteryConfiguration value"
            )

        if not isinstance(self.scenario, LoadScenario):
            raise TypeError(
                "scenario must be a LoadScenario value"
            )

        if (
            self.redundancy_mode
            is PVInverterRedundancyMode.NONE
            and self.redundant_inverters != 0
        ):
            raise ValueError(
                "NONE redundancy requires "
                "redundant_inverters to be 0"
            )

        if (
            self.redundancy_mode
            is PVInverterRedundancyMode.N_PLUS_1
            and self.redundant_inverters != 1
        ):
            raise ValueError(
                "N_PLUS_1 redundancy requires exactly "
                "one redundant inverter"
            )

        if (
            self.redundancy_mode
            is PVInverterRedundancyMode.TWO_N
            and self.redundant_inverters
            != self.duty_inverters
        ):
            raise ValueError(
                "TWO_N redundancy requires redundant_inverters "
                "to equal duty_inverters"
            )

        object.__setattr__(self, "code", normalized_code)
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "notes", normalized_notes)


__all__ = [
    "PVBatteryConfiguration",
    "PVInverterRedundancyMode",
    "PVPhaseConfiguration",
    "PVSizingInput",
    "PVSystemType",
]
