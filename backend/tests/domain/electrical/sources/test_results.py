"""
Unit tests for transformer source-sizing result models.
KESE-S2-M4
"""

from decimal import Decimal

import pytest

from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.models import (
    TransformerRedundancyMode,
)
from app.domain.electrical.sources.results import (
    TransformerSizingResult,
    TransformerSizingStatus,
    TransformerSizingWarning,
    TransformerSizingWarningCode,
)


def make_warning(
    *,
    code: TransformerSizingWarningCode = (
        TransformerSizingWarningCode.DERATING_APPLIED
    ),
    message: str = "Derating factors were applied.",
) -> TransformerSizingWarning:
    """Create a valid transformer-sizing warning."""

    return TransformerSizingWarning(
        code=code,
        message=message,
    )


def make_result(
    **overrides: object,
) -> TransformerSizingResult:
    """Create a valid selected-rating result."""

    payload: dict[str, object] = {
        "code": "TR-001",
        "name": "Main Transformer",
        "scenario": LoadScenario.NORMAL,
        "redundancy_mode": TransformerRedundancyMode.NONE,
        "demand_power_kw": Decimal("800"),
        "demand_power_factor": Decimal("0.80"),
        "base_demand_kva": Decimal("1000"),
        "future_growth_factor": Decimal("1"),
        "future_demand_kva": Decimal("1000"),
        "design_margin_factor": Decimal("1.10"),
        "design_required_kva": Decimal("1100"),
        "combined_derating_factor": Decimal("1"),
        "required_nameplate_capacity_kva": Decimal("1100"),
        "duty_units": 1,
        "standby_units": 0,
        "total_units": 1,
        "required_unit_rating_kva": Decimal("1100"),
        "selected_unit_rating_kva": Decimal("1250"),
        "installed_nameplate_capacity_kva": Decimal("1250"),
        "derated_duty_capacity_kva": Decimal("1250"),
        "spare_derated_capacity_kva": Decimal("150"),
        "loading_percent": Decimal("88"),
        "status": TransformerSizingStatus.VALID,
        "warnings": (),
    }

    payload.update(overrides)

    return TransformerSizingResult(
        **payload,  # type: ignore[arg-type]
    )


def make_no_solution_result(
    **overrides: object,
) -> TransformerSizingResult:
    """Create a valid no-solution result."""

    warning = make_warning(
        code=(
            TransformerSizingWarningCode
            .NO_STANDARD_RATING_AVAILABLE
        ),
        message="No suitable transformer rating is available.",
    )

    payload: dict[str, object] = {
        "selected_unit_rating_kva": None,
        "installed_nameplate_capacity_kva": None,
        "derated_duty_capacity_kva": None,
        "spare_derated_capacity_kva": None,
        "loading_percent": None,
        "status": TransformerSizingStatus.NO_SOLUTION,
        "warnings": (warning,),
    }

    payload.update(overrides)

    return make_result(**payload)


@pytest.mark.unit
def test_create_valid_transformer_sizing_warning() -> None:
    """A valid warning should preserve its controlled code."""

    warning = make_warning(
        message="  Derating factors were applied.  ",
    )

    assert (
        warning.code
        is TransformerSizingWarningCode.DERATING_APPLIED
    )
    assert warning.message == "Derating factors were applied."


@pytest.mark.unit
def test_invalid_warning_code_is_rejected() -> None:
    """Warning codes must use the controlled enum."""

    with pytest.raises(
        TypeError,
        match=(
            "code must be a "
            "TransformerSizingWarningCode value"
        ),
    ):
        TransformerSizingWarning(
            code="DERATING_APPLIED",  # type: ignore[arg-type]
            message="Invalid warning code",
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("message", "exception_type", "match"),
    [
        (
            100,
            TypeError,
            "warning message must be a string",
        ),
        (
            "   ",
            ValueError,
            "warning message must not be empty",
        ),
    ],
)
def test_invalid_warning_message_is_rejected(
    message: object,
    exception_type: type[Exception],
    match: str,
) -> None:
    """Warning messages must be non-empty strings."""

    with pytest.raises(
        exception_type,
        match=match,
    ):
        TransformerSizingWarning(
            code=TransformerSizingWarningCode.HIGH_LOADING,
            message=message,  # type: ignore[arg-type]
        )


@pytest.mark.unit
def test_create_valid_selected_rating_result() -> None:
    """A complete selected-rating result should be accepted."""

    result = make_result()

    assert result.code == "TR-001"
    assert result.selected_unit_rating_kva == Decimal("1250")
    assert result.total_units == 1
    assert result.status is TransformerSizingStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
def test_result_identifiers_are_trimmed() -> None:
    """Result identifiers should be normalized."""

    result = make_result(
        code="  TR-002  ",
        name="  Emergency Transformer  ",
    )

    assert result.code == "TR-002"
    assert result.name == "Emergency Transformer"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "field_value", "exception_type", "match"),
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
def test_invalid_result_identifiers_are_rejected(
    field_name: str,
    field_value: object,
    exception_type: type[Exception],
    match: str,
) -> None:
    """Result identifiers must be non-empty strings."""

    with pytest.raises(
        exception_type,
        match=match,
    ):
        make_result(
            **{field_name: field_value},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "field_value", "match"),
    [
        (
            "scenario",
            "NORMAL",
            "scenario must be a LoadScenario value",
        ),
        (
            "redundancy_mode",
            "NONE",
            "redundancy_mode must be a "
            "TransformerRedundancyMode value",
        ),
        (
            "status",
            "VALID",
            "status must be a TransformerSizingStatus value",
        ),
    ],
)
def test_invalid_result_enums_are_rejected(
    field_name: str,
    field_value: str,
    match: str,
) -> None:
    """Result enums must reject raw strings."""

    with pytest.raises(
        TypeError,
        match=match,
    ):
        make_result(
            **{field_name: field_value},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "demand_power_kw",
        "demand_power_factor",
        "base_demand_kva",
        "future_growth_factor",
        "future_demand_kva",
        "design_margin_factor",
        "design_required_kva",
        "combined_derating_factor",
        "required_nameplate_capacity_kva",
        "required_unit_rating_kva",
    ],
)
def test_float_result_values_are_rejected(
    field_name: str,
) -> None:
    """Result calculations must retain exact Decimal values."""

    with pytest.raises(
        TypeError,
        match=rf"{field_name} must be a Decimal",
    ):
        make_result(
            **{field_name: 1.0},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "demand_power_kw",
        "base_demand_kva",
        "future_demand_kva",
        "design_required_kva",
        "required_nameplate_capacity_kva",
        "required_unit_rating_kva",
    ],
)
def test_non_positive_capacity_values_are_rejected(
    field_name: str,
) -> None:
    """Required demand and capacity values must be positive."""

    with pytest.raises(
        ValueError,
        match=rf"{field_name} must be greater than zero",
    ):
        make_result(
            **{field_name: Decimal("0")},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("demand_power_factor", Decimal("0")),
        ("demand_power_factor", Decimal("1.01")),
        ("combined_derating_factor", Decimal("0")),
        ("combined_derating_factor", Decimal("1.01")),
    ],
)
def test_invalid_result_ratios_are_rejected(
    field_name: str,
    value: Decimal,
) -> None:
    """Power factor and derating factor must remain valid ratios."""

    with pytest.raises(ValueError):
        make_result(
            **{field_name: value},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "future_growth_factor",
        "design_margin_factor",
    ],
)
def test_result_factors_below_one_are_rejected(
    field_name: str,
) -> None:
    """Growth and margin factors must not be below one."""

    with pytest.raises(
        ValueError,
        match=rf"{field_name} must not be less than 1",
    ):
        make_result(
            **{field_name: Decimal("0.99")},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("duty_units", True),
        ("standby_units", False),
        ("total_units", Decimal("1")),
    ],
)
def test_invalid_unit_count_types_are_rejected(
    field_name: str,
    field_value: object,
) -> None:
    """Result unit counts must be integers."""

    with pytest.raises(
        TypeError,
        match=rf"{field_name} must be an integer",
    ):
        make_result(
            **{field_name: field_value},
        )


@pytest.mark.unit
def test_non_positive_duty_units_are_rejected() -> None:
    """At least one duty unit is required."""

    with pytest.raises(
        ValueError,
        match="duty_units must be greater than zero",
    ):
        make_result(
            duty_units=0,
            total_units=0,
        )


@pytest.mark.unit
def test_negative_standby_units_are_rejected() -> None:
    """Standby unit count cannot be negative."""

    with pytest.raises(
        ValueError,
        match="standby_units must not be negative",
    ):
        make_result(
            standby_units=-1,
            total_units=0,
        )


@pytest.mark.unit
def test_total_units_must_match_installed_units() -> None:
    """Total units must equal duty plus standby units."""

    with pytest.raises(
        ValueError,
        match=(
            "total_units must equal duty_units "
            "plus standby_units"
        ),
    ):
        make_result(
            total_units=2,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "redundancy_mode",
        "duty_units",
        "standby_units",
        "total_units",
        "match",
    ),
    [
        (
            TransformerRedundancyMode.NONE,
            1,
            1,
            2,
            "NONE redundancy requires standby_units to be 0",
        ),
        (
            TransformerRedundancyMode.N_PLUS_1,
            2,
            0,
            2,
            "N_PLUS_1 redundancy requires exactly one standby unit",
        ),
        (
            TransformerRedundancyMode.TWO_N,
            2,
            1,
            3,
            "TWO_N redundancy requires standby_units "
            "to equal duty_units",
        ),
    ],
)
def test_invalid_result_redundancy_is_rejected(
    redundancy_mode: TransformerRedundancyMode,
    duty_units: int,
    standby_units: int,
    total_units: int,
    match: str,
) -> None:
    """Result redundancy must agree with unit counts."""

    with pytest.raises(
        ValueError,
        match=match,
    ):
        make_result(
            redundancy_mode=redundancy_mode,
            duty_units=duty_units,
            standby_units=standby_units,
            total_units=total_units,
        )


@pytest.mark.unit
def test_warnings_must_be_a_tuple() -> None:
    """Warnings collection must be immutable."""

    with pytest.raises(
        TypeError,
        match="warnings must be a tuple",
    ):
        make_result(
            warnings=[],
        )


@pytest.mark.unit
def test_warning_collection_rejects_invalid_records() -> None:
    """Warnings tuple must contain structured warning records."""

    with pytest.raises(
        TypeError,
        match=(
            "warnings must contain only "
            "TransformerSizingWarning records"
        ),
    ):
        make_result(
            warnings=("invalid",),
        )


@pytest.mark.unit
def test_duplicate_warning_codes_are_rejected() -> None:
    """One result must not repeat a warning code."""

    first_warning = make_warning(
        message="First derating warning.",
    )
    second_warning = make_warning(
        message="Second derating warning.",
    )

    with pytest.raises(
        ValueError,
        match="warning codes must be unique",
    ):
        make_result(
            status=TransformerSizingStatus.WARNING,
            warnings=(
                first_warning,
                second_warning,
            ),
        )


@pytest.mark.unit
def test_missing_selected_rating_requires_no_solution_status() -> None:
    """A missing selected rating must be a no-solution result."""

    with pytest.raises(
        ValueError,
        match=(
            "missing selected rating requires "
            "NO_SOLUTION status"
        ),
    ):
        make_result(
            selected_unit_rating_kva=None,
        )


@pytest.mark.unit
def test_no_solution_requires_empty_capacity_results() -> None:
    """No-solution result cannot retain calculated selection outputs."""

    warning = make_warning(
        code=(
            TransformerSizingWarningCode
            .NO_STANDARD_RATING_AVAILABLE
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "capacity and loading results must be "
            "None when no rating is selected"
        ),
    ):
        make_result(
            selected_unit_rating_kva=None,
            status=TransformerSizingStatus.NO_SOLUTION,
            warnings=(warning,),
        )


@pytest.mark.unit
def test_no_solution_requires_standard_rating_warning() -> None:
    """No-solution status must include its controlled warning."""

    with pytest.raises(
        ValueError,
        match=(
            "NO_SOLUTION result requires "
            "NO_STANDARD_RATING_AVAILABLE warning"
        ),
    ):
        make_no_solution_result(
            warnings=(),
        )


@pytest.mark.unit
def test_create_valid_no_solution_result() -> None:
    """A complete no-solution result should be accepted."""

    result = make_no_solution_result()

    assert result.status is TransformerSizingStatus.NO_SOLUTION
    assert result.selected_unit_rating_kva is None
    assert result.loading_percent is None
    assert (
        result.warnings[0].code
        is TransformerSizingWarningCode
        .NO_STANDARD_RATING_AVAILABLE
    )


@pytest.mark.unit
def test_no_solution_status_rejects_selected_rating() -> None:
    """NO_SOLUTION status cannot contain a selected rating."""

    with pytest.raises(
        ValueError,
        match=(
            "NO_SOLUTION status cannot contain "
            "a selected rating"
        ),
    ):
        make_result(
            status=TransformerSizingStatus.NO_SOLUTION,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "installed_nameplate_capacity_kva",
        "derated_duty_capacity_kva",
        "spare_derated_capacity_kva",
        "loading_percent",
    ],
)
def test_selected_rating_requires_complete_outputs(
    field_name: str,
) -> None:
    """A selected rating requires all capacity and loading outputs."""

    with pytest.raises(
        ValueError,
        match=(
            "selected rating requires complete "
            "capacity and loading results"
        ),
    ):
        make_result(
            **{field_name: None},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "installed_nameplate_capacity_kva",
        "derated_duty_capacity_kva",
        "spare_derated_capacity_kva",
        "loading_percent",
    ],
)
def test_optional_result_floats_are_rejected(
    field_name: str,
) -> None:
    """Selected-rating outputs must remain exact Decimal values."""

    with pytest.raises(
        TypeError,
        match=rf"{field_name} must be a Decimal",
    ):
        make_result(
            **{field_name: 1.0},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "installed_nameplate_capacity_kva",
        "derated_duty_capacity_kva",
        "spare_derated_capacity_kva",
        "loading_percent",
    ],
)
def test_negative_selected_rating_outputs_are_rejected(
    field_name: str,
) -> None:
    """Selected-rating outputs cannot be negative."""

    with pytest.raises(
        ValueError,
        match=rf"{field_name} must not be negative",
    ):
        make_result(
            **{field_name: Decimal("-0.01")},
        )
