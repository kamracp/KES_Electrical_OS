"""
Unit tests for generator source-sizing domain models.
KESE-S2-M6
"""

from decimal import Decimal

import pytest

from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.generator_models import (
    GeneratorDutyClass,
    GeneratorRedundancyMode,
    GeneratorSizingInput,
)


def make_generator_input(
    **overrides: object,
) -> GeneratorSizingInput:
    """Create a valid generator-sizing input for tests."""

    payload: dict[str, object] = {
        "code": "DG-001",
        "name": "Emergency Generator",
        "steady_state_demand_kw": Decimal("800"),
        "steady_state_power_factor": Decimal("0.80"),
        "transient_step_load_kva": Decimal("350"),
        "transient_allowance_factor": Decimal("1.10"),
        "future_growth_factor": Decimal("1.10"),
        "design_margin_factor": Decimal("1.10"),
        "ambient_derating_factor": Decimal("0.95"),
        "altitude_derating_factor": Decimal("0.98"),
        "available_unit_ratings_kva": (
            Decimal("1000"),
            Decimal("1250"),
            Decimal("1600"),
            Decimal("2000"),
        ),
        "duty_units": 1,
        "standby_units": 0,
        "duty_class": GeneratorDutyClass.STANDBY,
        "redundancy_mode": GeneratorRedundancyMode.NONE,
        "scenario": LoadScenario.EMERGENCY,
        "notes": "Emergency electrical source",
    }

    payload.update(overrides)

    return GeneratorSizingInput(
        **payload,  # type: ignore[arg-type]
    )


@pytest.mark.unit
def test_create_valid_generator_sizing_input() -> None:
    """Valid input should preserve exact engineering values."""

    sizing_input = make_generator_input()

    assert sizing_input.code == "DG-001"
    assert sizing_input.name == "Emergency Generator"
    assert sizing_input.steady_state_demand_kw == Decimal("800")
    assert sizing_input.steady_state_power_factor == Decimal("0.80")
    assert sizing_input.transient_step_load_kva == Decimal("350")
    assert sizing_input.transient_allowance_factor == Decimal("1.10")
    assert sizing_input.duty_class is GeneratorDutyClass.STANDBY
    assert sizing_input.scenario is LoadScenario.EMERGENCY
    assert sizing_input.duty_units == 1
    assert sizing_input.standby_units == 0


@pytest.mark.unit
def test_generator_text_fields_are_normalized() -> None:
    """Text fields should be stripped and blank notes normalized."""

    sizing_input = make_generator_input(
        code="  DG-002  ",
        name="  Prime Generator  ",
        notes="   ",
    )

    assert sizing_input.code == "DG-002"
    assert sizing_input.name == "Prime Generator"
    assert sizing_input.notes is None


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "field_name",
        "field_value",
        "exception_type",
        "message",
    ),
    [
        (
            "code",
            123,
            TypeError,
            "code must be a string",
        ),
        (
            "name",
            None,
            TypeError,
            "name must be a string",
        ),
        (
            "code",
            "   ",
            ValueError,
            "code must not be empty",
        ),
        (
            "name",
            "\t",
            ValueError,
            "name must not be empty",
        ),
    ],
)
def test_invalid_generator_required_text_is_rejected(
    field_name: str,
    field_value: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """Required identifiers must be non-empty strings."""

    with pytest.raises(
        exception_type,
        match=message,
    ):
        make_generator_input(
            **{field_name: field_value},
        )


@pytest.mark.unit
def test_non_string_generator_notes_are_rejected() -> None:
    """Optional generator notes must be text or None."""

    with pytest.raises(
        TypeError,
        match="notes must be a string or None",
    ):
        make_generator_input(
            notes=100,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "steady_state_demand_kw",
        "steady_state_power_factor",
        "transient_step_load_kva",
        "transient_allowance_factor",
        "future_growth_factor",
        "design_margin_factor",
        "ambient_derating_factor",
        "altitude_derating_factor",
    ],
)
def test_generator_float_decimal_inputs_are_rejected(
    field_name: str,
) -> None:
    """Binary floating-point values must not enter calculations."""

    with pytest.raises(
        TypeError,
        match=rf"{field_name} must be a Decimal",
    ):
        make_generator_input(
            **{field_name: 0.95},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_non_finite_generator_demand_is_rejected(
    value: Decimal,
) -> None:
    """Non-finite generator demand values must not be accepted."""

    with pytest.raises(
        ValueError,
        match="steady_state_demand_kw must be finite",
    ):
        make_generator_input(
            steady_state_demand_kw=value,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_non_positive_generator_demand_is_rejected(
    value: Decimal,
) -> None:
    """Steady-state generator demand must exceed zero."""

    with pytest.raises(
        ValueError,
        match=(
            "steady_state_demand_kw "
            "must be greater than zero"
        ),
    ):
        make_generator_input(
            steady_state_demand_kw=value,
        )


@pytest.mark.unit
def test_negative_transient_step_load_is_rejected() -> None:
    """Transient step load must not be negative."""

    with pytest.raises(
        ValueError,
        match="transient_step_load_kva must not be negative",
    ):
        make_generator_input(
            transient_step_load_kva=Decimal("-0.01"),
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("steady_state_power_factor", Decimal("0")),
        ("steady_state_power_factor", Decimal("1.01")),
        ("ambient_derating_factor", Decimal("0")),
        ("ambient_derating_factor", Decimal("1.01")),
        ("altitude_derating_factor", Decimal("0")),
        ("altitude_derating_factor", Decimal("1.01")),
    ],
)
def test_invalid_generator_ratios_are_rejected(
    field_name: str,
    field_value: Decimal,
) -> None:
    """Power factor and derating ratios must remain valid."""

    with pytest.raises(ValueError):
        make_generator_input(
            **{field_name: field_value},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "transient_allowance_factor",
        "future_growth_factor",
        "design_margin_factor",
    ],
)
def test_generator_factors_below_one_are_rejected(
    field_name: str,
) -> None:
    """Engineering factors must not reduce requirements."""

    with pytest.raises(
        ValueError,
        match=rf"{field_name} must not be less than 1",
    ):
        make_generator_input(
            **{field_name: Decimal("0.99")},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("duty_units", True),
        ("duty_units", Decimal("1")),
        ("standby_units", False),
        ("standby_units", Decimal("0")),
    ],
)
def test_invalid_generator_unit_count_types_are_rejected(
    field_name: str,
    field_value: object,
) -> None:
    """Generator unit counts must be exact integers."""

    with pytest.raises(
        TypeError,
        match=rf"{field_name} must be an integer",
    ):
        make_generator_input(
            **{field_name: field_value},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "field_value", "message"),
    [
        (
            "duty_units",
            0,
            "duty_units must be greater than zero",
        ),
        (
            "standby_units",
            -1,
            "standby_units must not be negative",
        ),
    ],
)
def test_invalid_generator_unit_count_limits_are_rejected(
    field_name: str,
    field_value: int,
    message: str,
) -> None:
    """Duty and standby counts must remain valid."""

    with pytest.raises(
        ValueError,
        match=message,
    ):
        make_generator_input(
            **{field_name: field_value},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "field_value", "message"),
    [
        (
            "duty_class",
            "STANDBY",
            "duty_class must be a GeneratorDutyClass value",
        ),
        (
            "redundancy_mode",
            "NONE",
            (
                "redundancy_mode must be a "
                "GeneratorRedundancyMode value"
            ),
        ),
        (
            "scenario",
            "EMERGENCY",
            "scenario must be a LoadScenario value",
        ),
    ],
)
def test_invalid_generator_enum_values_are_rejected(
    field_name: str,
    field_value: str,
    message: str,
) -> None:
    """Controlled generator enums must reject raw strings."""

    with pytest.raises(
        TypeError,
        match=message,
    ):
        make_generator_input(
            **{field_name: field_value},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ratings", "exception_type", "message"),
    [
        (
            [Decimal("1000")],
            TypeError,
            "available_unit_ratings_kva must be a tuple",
        ),
        (
            (),
            ValueError,
            "at least one available generator rating is required",
        ),
    ],
)
def test_invalid_generator_rating_collections_are_rejected(
    ratings: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """The generator rating schedule must be a non-empty tuple."""

    with pytest.raises(
        exception_type,
        match=message,
    ):
        make_generator_input(
            available_unit_ratings_kva=ratings,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ratings", "exception_type", "message"),
    [
        (
            (1000.0,),
            TypeError,
            (
                "available_unit_ratings_kva rating "
                "must be a Decimal"
            ),
        ),
        (
            (Decimal("0"),),
            ValueError,
            (
                "available_unit_ratings_kva rating "
                "must be greater than zero"
            ),
        ),
    ],
)
def test_invalid_generator_rating_values_are_rejected(
    ratings: tuple[object, ...],
    exception_type: type[Exception],
    message: str,
) -> None:
    """Each generator rating must be a positive Decimal."""

    with pytest.raises(
        exception_type,
        match=message,
    ):
        make_generator_input(
            available_unit_ratings_kva=ratings,
        )


@pytest.mark.unit
def test_duplicate_generator_ratings_are_rejected() -> None:
    """Available generator ratings must be unique."""

    with pytest.raises(
        ValueError,
        match="available generator ratings must be unique",
    ):
        make_generator_input(
            available_unit_ratings_kva=(
                Decimal("1000"),
                Decimal("1000"),
            ),
        )


@pytest.mark.unit
def test_unsorted_generator_ratings_are_rejected() -> None:
    """Available generator ratings must be ascending."""

    with pytest.raises(
        ValueError,
        match=(
            "available generator ratings "
            "must be in ascending order"
        ),
    ):
        make_generator_input(
            available_unit_ratings_kva=(
                Decimal("1600"),
                Decimal("1000"),
            ),
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "redundancy_mode",
        "duty_units",
        "standby_units",
        "message",
    ),
    [
        (
            GeneratorRedundancyMode.NONE,
            1,
            1,
            "NONE redundancy requires standby_units to be 0",
        ),
        (
            GeneratorRedundancyMode.N_PLUS_1,
            2,
            0,
            (
                "N_PLUS_1 redundancy requires "
                "exactly one standby unit"
            ),
        ),
        (
            GeneratorRedundancyMode.TWO_N,
            2,
            1,
            (
                "TWO_N redundancy requires standby_units "
                "to equal duty_units"
            ),
        ),
    ],
)
def test_invalid_generator_redundancy_arrangements(
    redundancy_mode: GeneratorRedundancyMode,
    duty_units: int,
    standby_units: int,
    message: str,
) -> None:
    """Generator redundancy must match the unit arrangement."""

    with pytest.raises(
        ValueError,
        match=message,
    ):
        make_generator_input(
            redundancy_mode=redundancy_mode,
            duty_units=duty_units,
            standby_units=standby_units,
        )
