"""
Unit tests for electrical load and demand domain models.
KESE-S2-M1
"""

from decimal import Decimal

import pytest

from app.domain.electrical.loads.models import (
    LoadGroupInput,
    LoadInput,
    LoadScenario,
    PhaseSystem,
    PowerBasis,
)


def make_load(
    *,
    code: str = "MTR-001",
    power_factor: Decimal = Decimal("0.85"),
    phase_system: PhaseSystem = PhaseSystem.THREE_PHASE,
) -> LoadInput:
    """Create a valid test load."""

    return LoadInput(
        code=code,
        name="Process Water Pump",
        quantity=2,
        rated_power_kw=Decimal("15"),
        phase_system=phase_system,
        voltage_v=Decimal("415"),
        power_factor=power_factor,
        efficiency=Decimal("0.92"),
        utilization_factor=Decimal("0.80"),
        demand_factor=Decimal("0.90"),
        scenario=LoadScenario.NORMAL,
        power_basis=PowerBasis.MECHANICAL_OUTPUT,
        notes="Normal process load",
    )


@pytest.mark.unit
def test_create_valid_load() -> None:
    """A valid load should retain exact Decimal inputs."""

    load = make_load()

    assert load.code == "MTR-001"
    assert load.name == "Process Water Pump"
    assert load.quantity == 2
    assert load.rated_power_kw == Decimal("15")
    assert load.power_factor == Decimal("0.85")
    assert load.efficiency == Decimal("0.92")
    assert load.scenario is LoadScenario.NORMAL
    assert load.power_basis is PowerBasis.MECHANICAL_OUTPUT


@pytest.mark.unit
def test_load_text_fields_are_trimmed() -> None:
    """Leading and trailing spaces should be removed."""

    load = LoadInput(
        code="  LGT-001  ",
        name="  Lighting Load  ",
        quantity=1,
        rated_power_kw=Decimal("5"),
        phase_system=PhaseSystem.SINGLE_PHASE,
        voltage_v=Decimal("230"),
        notes="  Office lighting  ",
    )

    assert load.code == "LGT-001"
    assert load.name == "Lighting Load"
    assert load.notes == "Office lighting"


@pytest.mark.unit
def test_float_power_input_is_rejected() -> None:
    """Binary floating-point power values must not be accepted."""

    with pytest.raises(
        TypeError,
        match="rated_power_kw must be a Decimal",
    ):
        LoadInput(
            code="BAD-001",
            name="Invalid Float Load",
            quantity=1,
            rated_power_kw=15.0,  # type: ignore[arg-type]
            phase_system=PhaseSystem.THREE_PHASE,
            voltage_v=Decimal("415"),
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -1,
    ],
)
def test_non_positive_quantity_is_rejected(
    quantity: int,
) -> None:
    """A load quantity must be greater than zero."""

    with pytest.raises(
        ValueError,
        match="quantity must be greater than zero",
    ):
        LoadInput(
            code="BAD-QTY",
            name="Invalid Quantity",
            quantity=quantity,
            rated_power_kw=Decimal("10"),
            phase_system=PhaseSystem.THREE_PHASE,
            voltage_v=Decimal("415"),
        )


@pytest.mark.unit
def test_boolean_quantity_is_rejected() -> None:
    """Boolean values must not be accepted as integers."""

    with pytest.raises(
        TypeError,
        match="quantity must be an integer",
    ):
        LoadInput(
            code="BAD-BOOL",
            name="Boolean Quantity",
            quantity=True,  # type: ignore[arg-type]
            rated_power_kw=Decimal("10"),
            phase_system=PhaseSystem.THREE_PHASE,
            voltage_v=Decimal("415"),
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("power_factor", Decimal("0")),
        ("power_factor", Decimal("1.01")),
        ("efficiency", Decimal("0")),
        ("efficiency", Decimal("1.01")),
        ("utilization_factor", Decimal("-0.01")),
        ("utilization_factor", Decimal("1.01")),
        ("demand_factor", Decimal("-0.01")),
        ("demand_factor", Decimal("1.01")),
    ],
)
def test_invalid_ratios_are_rejected(
    field_name: str,
    field_value: Decimal,
) -> None:
    """Engineering ratios must remain within their allowed range."""

    payload = {
        "code": "BAD-RATIO",
        "name": "Invalid Ratio",
        "quantity": 1,
        "rated_power_kw": Decimal("10"),
        "phase_system": PhaseSystem.THREE_PHASE,
        "voltage_v": Decimal("415"),
        field_name: field_value,
    }

    with pytest.raises(ValueError):
        LoadInput(**payload)  # type: ignore[arg-type]


@pytest.mark.unit
def test_dc_load_requires_unity_power_factor() -> None:
    """DC loads must use a power factor of one."""

    with pytest.raises(
        ValueError,
        match="DC loads must use a power_factor of 1",
    ):
        make_load(
            phase_system=PhaseSystem.DC,
            power_factor=Decimal("0.90"),
        )


@pytest.mark.unit
def test_create_valid_load_group() -> None:
    """A valid group should preserve its loads and coincidence factor."""

    load = make_load()

    group = LoadGroupInput(
        code="PUMP-GRP",
        name="Process Pumps",
        loads=(load,),
        coincidence_factor=Decimal("0.90"),
    )

    assert group.code == "PUMP-GRP"
    assert group.name == "Process Pumps"
    assert group.loads == (load,)
    assert group.coincidence_factor == Decimal("0.90")


@pytest.mark.unit
def test_empty_load_group_is_rejected() -> None:
    """A group must contain at least one load."""

    with pytest.raises(
        ValueError,
        match="must contain at least one load",
    ):
        LoadGroupInput(
            code="EMPTY",
            name="Empty Group",
            loads=(),
        )


@pytest.mark.unit
def test_duplicate_load_codes_are_rejected() -> None:
    """Load codes must be unique within one group."""

    first_load = make_load(code="MTR-001")
    second_load = make_load(code="MTR-001")

    with pytest.raises(
        ValueError,
        match="load codes must be unique",
    ):
        LoadGroupInput(
            code="DUPLICATE-GRP",
            name="Duplicate Load Group",
            loads=(first_load, second_load),
        )