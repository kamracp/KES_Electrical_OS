"""
Unit tests for generator source-sizing result models.
KESE-S2-M6
"""

from decimal import Decimal

import pytest

from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.generator_models import (
    GeneratorDutyClass,
    GeneratorRedundancyMode,
)
from app.domain.electrical.sources.generator_results import (
    GeneratorSizingResult,
    GeneratorSizingStatus,
    GeneratorSizingWarning,
    GeneratorSizingWarningCode,
)


def make_warning(
    *,
    code: GeneratorSizingWarningCode = (
        GeneratorSizingWarningCode.DERATING_APPLIED
    ),
    message: str = "Generator derating was applied.",
) -> GeneratorSizingWarning:
    """Create a valid generator-sizing warning."""

    return GeneratorSizingWarning(
        code=code,
        message=message,
    )


def make_result(
    **overrides: object,
) -> GeneratorSizingResult:
    """Create a valid selected-rating result."""

    payload: dict[str, object] = {
        "code": "DG-001",
        "name": "Emergency Generator",
        "scenario": LoadScenario.EMERGENCY,
        "duty_class": GeneratorDutyClass.STANDBY,
        "redundancy_mode": GeneratorRedundancyMode.NONE,
        "steady_state_demand_kw": Decimal("800"),
        "steady_state_power_factor": Decimal("0.80"),
        "steady_state_demand_kva": Decimal("1000"),
        "future_growth_factor": Decimal("1"),
        "future_steady_state_kva": Decimal("1000"),
        "design_margin_factor": Decimal("1.10"),
        "steady_state_required_kva": Decimal("1100"),
        "transient_step_load_kva": Decimal("0"),
        "transient_allowance_factor": Decimal("1"),
        "transient_additional_kva": Decimal("0"),
        "transient_required_kva": Decimal("1000"),
        "governing_required_kva": Decimal("1100"),
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
        "steady_state_loading_percent": Decimal("88"),
        "status": GeneratorSizingStatus.VALID,
        "warnings": (),
    }

    payload.update(overrides)

    return GeneratorSizingResult(
        **payload,  # type: ignore[arg-type]
    )


def make_no_solution_result(
    **overrides: object,
) -> GeneratorSizingResult:
    """Create a valid no-solution result."""

    warning = make_warning(
        code=(
            GeneratorSizingWarningCode
            .NO_STANDARD_RATING_AVAILABLE
        ),
        message="No suitable generator rating is available.",
    )

    payload: dict[str, object] = {
        "selected_unit_rating_kva": None,
        "installed_nameplate_capacity_kva": None,
        "derated_duty_capacity_kva": None,
        "spare_derated_capacity_kva": None,
        "steady_state_loading_percent": None,
        "status": GeneratorSizingStatus.NO_SOLUTION,
        "warnings": (warning,),
    }

    payload.update(overrides)

    return make_result(**payload)


@pytest.mark.unit
def test_create_valid_generator_sizing_warning() -> None:
    """A valid warning should preserve its controlled code."""

    warning = make_warning(
        message="  Generator derating was applied.  ",
    )

    assert (
        warning.code
        is GeneratorSizingWarningCode.DERATING_APPLIED
    )
    assert warning.message == "Generator derating was applied."


@pytest.mark.unit
def test_invalid_generator_warning_code_is_rejected() -> None:
    """Warning codes must use the controlled enum."""

    with pytest.raises(
        TypeError,
        match=(
            "code must be a "
            "GeneratorSizingWarningCode value"
        ),
    ):
        GeneratorSizingWarning(
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
def test_invalid_generator_warning_message_is_rejected(
    message: object,
    exception_type: type[Exception],
    match: str,
) -> None:
    """Warning messages must be non-empty strings."""

    with pytest.raises(
        exception_type,
        match=match,
    ):
        GeneratorSizingWarning(
            code=GeneratorSizingWarningCode.HIGH_LOADING,
            message=message,  # type: ignore[arg-type]
        )


@pytest.mark.unit
def test_create_valid_generator_selected_result() -> None:
    """A complete selected-rating result should be accepted."""

    result = make_result()

    assert result.code == "DG-001"
    assert result.selected_unit_rating_kva == Decimal("1250")
    assert result.total_units == 1
    assert result.status is GeneratorSizingStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
def test_generator_result_identifiers_are_trimmed() -> None:
    """Result identifiers should be normalized."""

    result = make_result(
        code="  DG-002  ",
        name="  Prime Generator  ",
    )

    assert result.code == "DG-002"
    assert result.name == "Prime Generator"


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
def test_invalid_generator_result_identifiers_are_rejected(
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
            "EMERGENCY",
            "scenario must be a LoadScenario value",
        ),
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
            "status",
            "VALID",
            "status must be a GeneratorSizingStatus value",
        ),
    ],
)
def test_invalid_generator_result_enums_are_rejected(
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
        "steady_state_demand_kw",
        "steady_state_power_factor",
        "steady_state_demand_kva",
        "future_growth_factor",
        "future_steady_state_kva",
        "design_margin_factor",
        "steady_state_required_kva",
        "transient_step_load_kva",
        "transient_allowance_factor",
        "transient_additional_kva",
        "transient_required_kva",
        "governing_required_kva",
        "combined_derating_factor",
        "required_nameplate_capacity_kva",
        "required_unit_rating_kva",
    ],
)
def test_float_generator_result_values_are_rejected(
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
        "steady_state_demand_kw",
        "steady_state_demand_kva",
        "future_steady_state_kva",
        "steady_state_required_kva",
        "transient_required_kva",
        "governing_required_kva",
        "required_nameplate_capacity_kva",
        "required_unit_rating_kva",
    ],
)
def test_non_positive_generator_capacity_values_are_rejected(
    field_name: str,
) -> None:
    """Required generator demand and capacity must be positive."""

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
        ("steady_state_power_factor", Decimal("0")),
        ("steady_state_power_factor", Decimal("1.01")),
        ("combined_derating_factor", Decimal("0")),
        ("combined_derating_factor", Decimal("1.01")),
    ],
)
def test_invalid_generator_result_ratios_are_rejected(
    field_name: str,
    value: Decimal,
) -> None:
    """Power factor and derating must remain valid ratios."""

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
        "transient_allowance_factor",
    ],
)
def test_generator_result_factors_below_one_are_rejected(
    field_name: str,
) -> None:
    """Growth, margin and transient factors cannot reduce demand."""

    with pytest.raises(
        ValueError,
        match=rf"{field_name} must not be less than 1",
    ):
        make_result(
            **{field_name: Decimal("0.99")},
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "field_name",
    [
        "transient_step_load_kva",
        "transient_additional_kva",
    ],
)
def test_negative_transient_result_values_are_rejected(
    field_name: str,
) -> None:
    """Transient values must not be negative."""

    with pytest.raises(
        ValueError,
        match=rf"{field_name} must not be negative",
    ):
        make_result(
            **{field_name: Decimal("-0.01")},
        )


@pytest.mark.unit
def test_governing_capacity_cannot_be_below_steady_state() -> None:
    """Governing capacity must cover steady-state requirement."""

    with pytest.raises(
        ValueError,
        match=(
            "governing_required_kva must not be below "
            "steady_state_required_kva"
        ),
    ):
        make_result(
            governing_required_kva=Decimal("1099"),
        )


@pytest.mark.unit
def test_governing_capacity_cannot_be_below_transient() -> None:
    """Governing capacity must cover transient requirement."""

    with pytest.raises(
        ValueError,
        match=(
            "governing_required_kva must not be below "
            "transient_required_kva"
        ),
    ):
        make_result(
            transient_required_kva=Decimal("1200"),
            governing_required_kva=Decimal("1100"),
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
def test_invalid_generator_result_unit_types_are_rejected(
    field_name: str,
    field_value: object,
) -> None:
    """Generator result unit counts must be integers."""

    with pytest.raises(
        TypeError,
        match=rf"{field_name} must be an integer",
    ):
        make_result(
            **{field_name: field_value},
        )


@pytest.mark.unit
def test_non_positive_generator_duty_units_are_rejected() -> None:
    """At least one duty generator is required."""

    with pytest.raises(
        ValueError,
        match="duty_units must be greater than zero",
    ):
        make_result(
            duty_units=0,
            total_units=0,
        )


@pytest.mark.unit
def test_negative_generator_standby_units_are_rejected() -> None:
    """Standby generator count cannot be negative."""

    with pytest.raises(
        ValueError,
        match="standby_units must not be negative",
    ):
        make_result(
            standby_units=-1,
            total_units=0,
        )


@pytest.mark.unit
def test_generator_total_units_must_match() -> None:
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
            GeneratorRedundancyMode.NONE,
            1,
            1,
            2,
            "NONE redundancy requires standby_units to be 0",
        ),
        (
            GeneratorRedundancyMode.N_PLUS_1,
            2,
            0,
            2,
            (
                "N_PLUS_1 redundancy requires "
                "exactly one standby unit"
            ),
        ),
        (
            GeneratorRedundancyMode.TWO_N,
            2,
            1,
            3,
            (
                "TWO_N redundancy requires standby_units "
                "to equal duty_units"
            ),
        ),
    ],
)
def test_invalid_generator_result_redundancy(
    redundancy_mode: GeneratorRedundancyMode,
    duty_units: int,
    standby_units: int,
    total_units: int,
    match: str,
) -> None:
    """Result redundancy must match installed unit counts."""

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
def test_generator_warnings_must_be_tuple() -> None:
    """Warnings must use an immutable tuple."""

    with pytest.raises(
        TypeError,
        match="warnings must be a tuple",
    ):
        make_result(
            warnings=[],  # type: ignore[arg-type]
        )


@pytest.mark.unit
def test_generator_warning_records_are_required() -> None:
    """Warnings tuple must contain controlled warning records."""

    with pytest.raises(
        TypeError,
        match=(
            "warnings must contain only "
            "GeneratorSizingWarning records"
        ),
    ):
        make_result(
            warnings=("invalid",),
        )


@pytest.mark.unit
def test_duplicate_generator_warning_codes_are_rejected() -> None:
    """Each warning code may appear only once."""

    with pytest.raises(
        ValueError,
        match="warning codes must be unique",
    ):
        make_result(
            warnings=(
                make_warning(message="First warning"),
                make_warning(message="Second warning"),
            ),
        )


@pytest.mark.unit
def test_create_valid_generator_no_solution_result() -> None:
    """A complete no-solution result should be accepted."""

    result = make_no_solution_result()

    assert result.status is GeneratorSizingStatus.NO_SOLUTION
    assert result.selected_unit_rating_kva is None
    assert result.installed_nameplate_capacity_kva is None
    assert len(result.warnings) == 1


@pytest.mark.unit
def test_missing_selected_rating_requires_no_solution() -> None:
    """Missing rating must use NO_SOLUTION status."""

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
def test_no_solution_cannot_contain_selected_rating() -> None:
    """NO_SOLUTION cannot retain a selected rating."""

    with pytest.raises(
        ValueError,
        match=(
            "NO_SOLUTION status cannot contain "
            "a selected rating"
        ),
    ):
        make_result(
            status=GeneratorSizingStatus.NO_SOLUTION,
        )


@pytest.mark.unit
def test_no_solution_capacity_outputs_must_be_none() -> None:
    """No-solution result cannot contain capacity outputs."""

    with pytest.raises(
        ValueError,
        match=(
            "capacity and loading results must be "
            "None when no rating is selected"
        ),
    ):
        make_no_solution_result(
            installed_nameplate_capacity_kva=Decimal("1250"),
        )


@pytest.mark.unit
def test_no_solution_requires_controlled_warning() -> None:
    """No-solution result requires the matching warning code."""

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
@pytest.mark.parametrize(
    "field_name",
    [
        "installed_nameplate_capacity_kva",
        "derated_duty_capacity_kva",
        "spare_derated_capacity_kva",
        "steady_state_loading_percent",
    ],
)
def test_selected_rating_requires_complete_outputs(
    field_name: str,
) -> None:
    """Selected rating requires all capacity outputs."""

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
        "steady_state_loading_percent",
    ],
)
def test_selected_generator_outputs_cannot_be_negative(
    field_name: str,
) -> None:
    """Selected-rating outputs must not be negative."""

    with pytest.raises(
        ValueError,
        match=rf"{field_name} must not be negative",
    ):
        make_result(
            **{field_name: Decimal("-0.01")},
        )
