from decimal import Decimal

import pytest

from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.ups_models import (
    UPSBatteryTechnology,
    UPSPhaseConfiguration,
    UPSRedundancyMode,
    UPSSizingInput,
    UPSTopology,
)


def _valid_input(
    **overrides: object,
) -> UPSSizingInput:
    values: dict[str, object] = {
        "code": " UPS-01 ",
        "name": " Critical Process UPS ",
        "critical_load_kw": Decimal("120"),
        "load_power_factor": Decimal("0.90"),
        "ups_efficiency": Decimal("0.94"),
        "inverter_overload_factor": Decimal("1"),
        "future_growth_factor": Decimal("1.10"),
        "design_margin_factor": Decimal("1.20"),
        "ambient_derating_factor": Decimal("0.95"),
        "altitude_derating_factor": Decimal("1"),
        "required_runtime_minutes": Decimal("30"),
        "available_unit_ratings_kva": (
            Decimal("80"),
            Decimal("100"),
            Decimal("120"),
            Decimal("160"),
        ),
        "duty_modules": 2,
        "redundant_modules": 1,
        "topology": UPSTopology.ONLINE_DOUBLE_CONVERSION,
        "phase_configuration": UPSPhaseConfiguration.THREE_PHASE,
        "redundancy_mode": UPSRedundancyMode.N_PLUS_1,
        "battery_technology": UPSBatteryTechnology.VRLA,
        "scenario": LoadScenario.EMERGENCY,
        "notes": "  Critical UPS system  ",
    }

    values.update(overrides)

    return UPSSizingInput(**values)


def test_ups_input_normalizes_text() -> None:
    sizing_input = _valid_input()

    assert sizing_input.code == "UPS-01"
    assert sizing_input.name == "Critical Process UPS"
    assert sizing_input.notes == "Critical UPS system"


def test_ups_input_normalizes_blank_notes_to_none() -> None:
    sizing_input = _valid_input(
        notes="   ",
    )

    assert sizing_input.notes is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("critical_load_kw", Decimal("0")),
        ("required_runtime_minutes", Decimal("0")),
    ],
)
def test_ups_input_requires_positive_values(
    field_name: str,
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be greater than zero",
    ):
        _valid_input(
            **{field_name: value},
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("load_power_factor", Decimal("0")),
        ("load_power_factor", Decimal("1.01")),
        ("ups_efficiency", Decimal("0")),
        ("ambient_derating_factor", Decimal("1.01")),
        ("altitude_derating_factor", Decimal("-0.1")),
    ],
)
def test_ups_input_rejects_invalid_ratios(
    field_name: str,
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="greater than 0 and not greater than 1",
    ):
        _valid_input(
            **{field_name: value},
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("inverter_overload_factor", Decimal("0.99")),
        ("future_growth_factor", Decimal("0.99")),
        ("design_margin_factor", Decimal("0.99")),
    ],
)
def test_ups_input_rejects_factors_below_one(
    field_name: str,
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="must not be less than 1",
    ):
        _valid_input(
            **{field_name: value},
        )


def test_ups_input_requires_available_ratings() -> None:
    with pytest.raises(
        ValueError,
        match="at least one available UPS rating",
    ):
        _valid_input(
            available_unit_ratings_kva=(),
        )


def test_ups_input_rejects_duplicate_ratings() -> None:
    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        _valid_input(
            available_unit_ratings_kva=(
                Decimal("100"),
                Decimal("100"),
            ),
        )


def test_ups_input_requires_none_redundancy_consistency() -> None:
    with pytest.raises(
        ValueError,
        match="redundant_modules to be 0",
    ):
        _valid_input(
            redundancy_mode=UPSRedundancyMode.NONE,
            redundant_modules=1,
        )


def test_ups_input_requires_two_n_consistency() -> None:
    with pytest.raises(
        ValueError,
        match="to equal duty_modules",
    ):
        _valid_input(
            redundancy_mode=UPSRedundancyMode.TWO_N,
            duty_modules=2,
            redundant_modules=1,
        )


def test_ups_input_accepts_two_n_configuration() -> None:
    sizing_input = _valid_input(
        redundancy_mode=UPSRedundancyMode.TWO_N,
        duty_modules=2,
        redundant_modules=2,
    )

    assert sizing_input.duty_modules == 2
    assert sizing_input.redundant_modules == 2


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("duty_modules", True, "must be an integer"),
        ("duty_modules", 0, "must be greater than zero"),
        ("redundant_modules", True, "must be an integer"),
        ("redundant_modules", -1, "must not be negative"),
    ],
)
def test_ups_input_validates_module_counts(
    field_name: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(
        (TypeError, ValueError),
        match=message,
    ):
        _valid_input(
            **{field_name: value},
        )
