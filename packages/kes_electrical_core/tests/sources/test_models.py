"""
Unit tests for transformer source-sizing domain models.
KESE-S2-M4
"""

from decimal import Decimal

import pytest

from kes_electrical_core.loads.models import LoadScenario
from kes_electrical_core.sources.models import (
    TransformerRedundancyMode,
    TransformerSizingInput,
)


def make_sizing_input(
    **overrides: object,
) -> TransformerSizingInput:
    """Create a valid transformer-sizing input for tests."""

    payload: dict[str, object] = {
        "code": "TR-001",
        "name": "Main Transformer",
        "demand_power_kw": Decimal("800"),
        "demand_power_factor": Decimal("0.80"),
        "available_unit_ratings_kva": (
            Decimal("1000"),
            Decimal("1250"),
            Decimal("1600"),
        ),
        "future_growth_factor": Decimal("1"),
        "design_margin_factor": Decimal("1.10"),
        "ambient_derating_factor": Decimal("1"),
        "altitude_derating_factor": Decimal("1"),
        "harmonic_derating_factor": Decimal("1"),
        "duty_units": 1,
        "standby_units": 0,
        "redundancy_mode": TransformerRedundancyMode.NONE,
        "scenario": LoadScenario.NORMAL,
        "notes": "Main electrical source",
    }

    payload.update(overrides)

    return TransformerSizingInput(
        **payload,  # type: ignore[arg-type]
    )


@pytest.mark.unit
def test_create_valid_transformer_sizing_input() -> None:
    """Valid input should preserve exact engineering values."""

    sizing_input = make_sizing_input()

    assert sizing_input.code == "TR-001"
    assert sizing_input.name == "Main Transformer"
    assert sizing_input.demand_power_kw == Decimal("800")
    assert sizing_input.demand_power_factor == Decimal("0.80")
    assert sizing_input.design_margin_factor == Decimal("1.10")
    assert sizing_input.duty_units == 1
    assert sizing_input.standby_units == 0
    assert (
        sizing_input.redundancy_mode
        is TransformerRedundancyMode.NONE
    )
    assert sizing_input.scenario is LoadScenario.NORMAL


@pytest.mark.unit
def test_text_fields_are_normalized() -> None:
    """Text fields should be stripped and blank notes normalized."""

    sizing_input = make_sizing_input(
        code="  TR-002  ",
        name="  Emergency Transformer  ",
        notes="   ",
    )

    assert sizing_input.code == "TR-002"
    assert sizing_input.name == "Emergency Transformer"
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
def test_invalid_required_text_is_rejected(
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
        make_sizing_input(
            **{field_name: field_value},
        )


@pytest.mark.unit
def test_non_string_notes_are_rejected() -> None:
    """Optional notes must be text or None."""

    with pytest.raises(
        TypeError,
        match="notes must be a string or None",
    ):
        make_sizing_input(
            notes=100,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "demand_power_kw",
        "demand_power_factor",
        "future_growth_factor",
        "design_margin_factor",
        "ambient_derating_factor",
        "altitude_derating_factor",
        "harmonic_derating_factor",
    ],
)
def test_float_decimal_inputs_are_rejected(
    field_name: str,
) -> None:
    """Binary floating-point values must not enter calculations."""

    with pytest.raises(
        TypeError,
        match=rf"{field_name} must be a Decimal",
    ):
        make_sizing_input(
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
def test_non_finite_demand_power_is_rejected(
    value: Decimal,
) -> None:
    """Non-finite Decimal values must not be accepted."""

    with pytest.raises(
        ValueError,
        match="demand_power_kw must be finite",
    ):
        make_sizing_input(
            demand_power_kw=value,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_non_positive_demand_power_is_rejected(
    value: Decimal,
) -> None:
    """Transformer demand must be greater than zero."""

    with pytest.raises(
        ValueError,
        match="demand_power_kw must be greater than zero",
    ):
        make_sizing_input(
            demand_power_kw=value,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("demand_power_factor", Decimal("0")),
        ("demand_power_factor", Decimal("1.01")),
        ("ambient_derating_factor", Decimal("0")),
        ("ambient_derating_factor", Decimal("1.01")),
        ("altitude_derating_factor", Decimal("0")),
        ("altitude_derating_factor", Decimal("1.01")),
        ("harmonic_derating_factor", Decimal("0")),
        ("harmonic_derating_factor", Decimal("1.01")),
    ],
)
def test_invalid_ratios_are_rejected(
    field_name: str,
    field_value: Decimal,
) -> None:
    """Power factor and derating ratios must remain within limits."""

    with pytest.raises(ValueError):
        make_sizing_input(
            **{field_name: field_value},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "future_growth_factor",
        "design_margin_factor",
    ],
)
def test_engineering_factors_below_one_are_rejected(
    field_name: str,
) -> None:
    """Growth and design factors must not reduce demand."""

    with pytest.raises(
        ValueError,
        match=rf"{field_name} must not be less than 1",
    ):
        make_sizing_input(
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
def test_invalid_unit_count_types_are_rejected(
    field_name: str,
    field_value: object,
) -> None:
    """Unit counts must be integers and must reject booleans."""

    with pytest.raises(
        TypeError,
        match=rf"{field_name} must be an integer",
    ):
        make_sizing_input(
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
def test_invalid_unit_count_limits_are_rejected(
    field_name: str,
    field_value: int,
    message: str,
) -> None:
    """Duty and standby unit counts must remain valid."""

    with pytest.raises(
        ValueError,
        match=message,
    ):
        make_sizing_input(
            **{field_name: field_value},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "field_value", "message"),
    [
        (
            "redundancy_mode",
            "NONE",
            "redundancy_mode must be a "
            "TransformerRedundancyMode value",
        ),
        (
            "scenario",
            "NORMAL",
            "scenario must be a LoadScenario value",
        ),
    ],
)
def test_invalid_enum_values_are_rejected(
    field_name: str,
    field_value: str,
    message: str,
) -> None:
    """Controlled engineering enums must not accept raw strings."""

    with pytest.raises(
        TypeError,
        match=message,
    ):
        make_sizing_input(
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
            "at least one available transformer rating is required",
        ),
    ],
)
def test_invalid_rating_collections_are_rejected(
    ratings: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """The controlled rating schedule must be a non-empty tuple."""

    with pytest.raises(
        exception_type,
        match=message,
    ):
        make_sizing_input(
            available_unit_ratings_kva=ratings,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ratings", "exception_type", "message"),
    [
        (
            (1000.0,),
            TypeError,
            "available_unit_ratings_kva rating "
            "must be a Decimal",
        ),
        (
            (Decimal("0"),),
            ValueError,
            "available_unit_ratings_kva rating "
            "must be greater than zero",
        ),
    ],
)
def test_invalid_rating_values_are_rejected(
    ratings: tuple[object, ...],
    exception_type: type[Exception],
    message: str,
) -> None:
    """Each available rating must be an exact positive Decimal."""

    with pytest.raises(
        exception_type,
        match=message,
    ):
        make_sizing_input(
            available_unit_ratings_kva=ratings,
        )


@pytest.mark.unit
def test_duplicate_transformer_ratings_are_rejected() -> None:
    """Available transformer ratings must be unique."""

    with pytest.raises(
        ValueError,
        match="available transformer ratings must be unique",
    ):
        make_sizing_input(
            available_unit_ratings_kva=(
                Decimal("1000"),
                Decimal("1000"),
            ),
        )


@pytest.mark.unit
def test_unsorted_transformer_ratings_are_rejected() -> None:
    """Available ratings must follow ascending order."""

    with pytest.raises(
        ValueError,
        match=(
            "available transformer ratings "
            "must be in ascending order"
        ),
    ):
        make_sizing_input(
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
            TransformerRedundancyMode.NONE,
            1,
            1,
            "NONE redundancy requires standby_units to be 0",
        ),
        (
            TransformerRedundancyMode.N_PLUS_1,
            2,
            0,
            "N_PLUS_1 redundancy requires exactly one standby unit",
        ),
        (
            TransformerRedundancyMode.TWO_N,
            2,
            1,
            "TWO_N redundancy requires standby_units "
            "to equal duty_units",
        ),
    ],
)
def test_invalid_redundancy_arrangements_are_rejected(
    redundancy_mode: TransformerRedundancyMode,
    duty_units: int,
    standby_units: int,
    message: str,
) -> None:
    """Redundancy mode must agree with installed unit counts."""

    with pytest.raises(
        ValueError,
        match=message,
    ):
        make_sizing_input(
            redundancy_mode=redundancy_mode,
            duty_units=duty_units,
            standby_units=standby_units,
        )
