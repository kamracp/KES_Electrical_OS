"""
Domain input models for UPS source sizing.

Mission: KESE-S2-M7
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.loads.models import LoadScenario


class UPSTopology(StrEnum):
    """UPS conversion topology."""

    OFFLINE = "OFFLINE"
    LINE_INTERACTIVE = "LINE_INTERACTIVE"
    ONLINE_DOUBLE_CONVERSION = "ONLINE_DOUBLE_CONVERSION"


class UPSPhaseConfiguration(StrEnum):
    """UPS input/output phase arrangement."""

    SINGLE_PHASE = "SINGLE_PHASE"
    THREE_PHASE = "THREE_PHASE"


class UPSRedundancyMode(StrEnum):
    """UPS module redundancy arrangement."""

    NONE = "NONE"
    N_PLUS_1 = "N_PLUS_1"
    TWO_N = "TWO_N"


class UPSBatteryTechnology(StrEnum):
    """Supported UPS battery technology classification."""

    VRLA = "VRLA"
    LITHIUM_ION = "LITHIUM_ION"
    NICKEL_CADMIUM = "NICKEL_CADMIUM"


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


def _require_non_negative_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    """Require a Decimal value equal to or greater than zero."""

    _require_decimal(field_name, value)

    if value < Decimal("0"):
        raise ValueError(
            f"{field_name} must not be negative"
        )


def _require_ratio(
    field_name: str,
    value: Decimal,
) -> None:
    """Require a ratio greater than zero and not greater than one."""

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
    """Require an engineering factor equal to or greater than one."""

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
class UPSSizingInput:
    """
    Immutable UPS source-sizing input.

    critical_load_kw is the simultaneous active power demand that must remain
    available through the UPS.

    load_power_factor is the aggregate output power factor of the protected
    loads.

    ups_efficiency represents the expected operating efficiency at the design
    loading condition.

    inverter_overload_factor allows for short-duration load pickup, transformer
    inrush or controlled transient demand. It must be based on the approved
    UPS design basis.

    available_unit_ratings_kva must contain unique standard UPS ratings in
    ascending order.
    """

    code: str
    name: str

    critical_load_kw: Decimal
    load_power_factor: Decimal

    ups_efficiency: Decimal = Decimal("0.94")
    inverter_overload_factor: Decimal = Decimal("1")

    future_growth_factor: Decimal = Decimal("1")
    design_margin_factor: Decimal = Decimal("1.20")

    ambient_derating_factor: Decimal = Decimal("1")
    altitude_derating_factor: Decimal = Decimal("1")

    required_runtime_minutes: Decimal = Decimal("30")

    available_unit_ratings_kva: tuple[Decimal, ...] = ()

    duty_modules: int = 1
    redundant_modules: int = 0

    topology: UPSTopology = UPSTopology.ONLINE_DOUBLE_CONVERSION
    phase_configuration: UPSPhaseConfiguration = (
        UPSPhaseConfiguration.THREE_PHASE
    )
    redundancy_mode: UPSRedundancyMode = UPSRedundancyMode.NONE
    battery_technology: UPSBatteryTechnology = UPSBatteryTechnology.VRLA

    scenario: LoadScenario = LoadScenario.EMERGENCY

    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize UPS-sizing input data."""

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
            "critical_load_kw",
            self.critical_load_kw,
        )
        _require_ratio(
            "load_power_factor",
            self.load_power_factor,
        )
        _require_ratio(
            "ups_efficiency",
            self.ups_efficiency,
        )
        _require_factor_not_below_one(
            "inverter_overload_factor",
            self.inverter_overload_factor,
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
        _require_positive_decimal(
            "required_runtime_minutes",
            self.required_runtime_minutes,
        )

        if (
            isinstance(self.duty_modules, bool)
            or not isinstance(self.duty_modules, int)
        ):
            raise TypeError(
                "duty_modules must be an integer"
            )

        if self.duty_modules <= 0:
            raise ValueError(
                "duty_modules must be greater than zero"
            )

        if (
            isinstance(self.redundant_modules, bool)
            or not isinstance(self.redundant_modules, int)
        ):
            raise TypeError(
                "redundant_modules must be an integer"
            )

        if self.redundant_modules < 0:
            raise ValueError(
                "redundant_modules must not be negative"
            )

        if not isinstance(
            self.topology,
            UPSTopology,
        ):
            raise TypeError(
                "topology must be a UPSTopology value"
            )

        if not isinstance(
            self.phase_configuration,
            UPSPhaseConfiguration,
        ):
            raise TypeError(
                "phase_configuration must be a "
                "UPSPhaseConfiguration value"
            )

        if not isinstance(
            self.redundancy_mode,
            UPSRedundancyMode,
        ):
            raise TypeError(
                "redundancy_mode must be a "
                "UPSRedundancyMode value"
            )

        if not isinstance(
            self.battery_technology,
            UPSBatteryTechnology,
        ):
            raise TypeError(
                "battery_technology must be a "
                "UPSBatteryTechnology value"
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
                "at least one available UPS rating is required"
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
                "available UPS ratings must be unique"
            )

        if self.available_unit_ratings_kva != tuple(
            sorted(self.available_unit_ratings_kva)
        ):
            raise ValueError(
                "available UPS ratings must be in ascending order"
            )

        if (
            self.redundancy_mode is UPSRedundancyMode.NONE
            and self.redundant_modules != 0
        ):
            raise ValueError(
                "NONE redundancy requires redundant_modules to be 0"
            )

        if (
            self.redundancy_mode is UPSRedundancyMode.N_PLUS_1
            and self.redundant_modules != 1
        ):
            raise ValueError(
                "N_PLUS_1 redundancy requires exactly "
                "one redundant module"
            )

        if (
            self.redundancy_mode is UPSRedundancyMode.TWO_N
            and self.redundant_modules != self.duty_modules
        ):
            raise ValueError(
                "TWO_N redundancy requires redundant_modules "
                "to equal duty_modules"
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
    "UPSBatteryTechnology",
    "UPSPhaseConfiguration",
    "UPSRedundancyMode",
    "UPSSizingInput",
    "UPSTopology",
]
