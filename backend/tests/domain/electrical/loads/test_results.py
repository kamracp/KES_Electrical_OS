"""
Unit tests for electrical load calculation result models.
KESE-S2-M1
"""

from decimal import Decimal

import pytest

from app.domain.electrical.loads.models import (
    LoadScenario,
    PhaseSystem,
)
from app.domain.electrical.loads.results import (
    GROUP_COINCIDENCE_ASSUMPTION,
    CalculationStatus,
    CalculationWarning,
    LoadCalculationResult,
    LoadGroupCalculationResult,
    LoadWarningCode,
    resolve_status,
)


def make_load_result(
    *,
    load_code: str = "MTR-001",
    status: CalculationStatus = CalculationStatus.VALID,
    warnings: tuple[CalculationWarning, ...] = (),
) -> LoadCalculationResult:
    """Create a valid load calculation result."""

    return LoadCalculationResult(
        load_code=load_code,
        load_name="Process Water Pump",
        scenario=LoadScenario.NORMAL,
        phase_system=PhaseSystem.THREE_PHASE,
        connected_power_kw=Decimal("32.6087"),
        utilized_power_kw=Decimal("26.0870"),
        demand_power_kw=Decimal("23.4783"),
        apparent_power_kva=Decimal("27.6215"),
        reactive_power_kvar=Decimal("14.5380"),
        design_current_a=Decimal("38.4250"),
        status=status,
        warnings=warnings,
    )


@pytest.mark.unit
def test_create_calculation_warning() -> None:
    """A warning should retain its controlled code and trimmed message."""

    warning = CalculationWarning(
        code=LoadWarningCode.DEMAND_FACTOR_NOT_ESTABLISHED,
        message="  Demand factor is not established.  ",
    )

    assert warning.code is LoadWarningCode.DEMAND_FACTOR_NOT_ESTABLISHED
    assert warning.message == "Demand factor is not established."


@pytest.mark.unit
def test_empty_warning_message_is_rejected() -> None:
    """A structured warning must contain a message."""

    with pytest.raises(
        ValueError,
        match="warning message must not be empty",
    ):
        CalculationWarning(
            code=LoadWarningCode.ZERO_DEMAND,
            message="   ",
        )


@pytest.mark.unit
def test_create_valid_load_result() -> None:
    """A valid result should preserve exact Decimal values."""

    result = make_load_result()

    assert result.load_code == "MTR-001"
    assert result.connected_power_kw == Decimal("32.6087")
    assert result.demand_power_kw == Decimal("23.4783")
    assert result.apparent_power_kva == Decimal("27.6215")
    assert result.design_current_a == Decimal("38.4250")
    assert result.status is CalculationStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
def test_result_text_fields_are_trimmed() -> None:
    """Result identifiers and names should be normalized."""

    result = LoadCalculationResult(
        load_code="  LGT-001  ",
        load_name="  Office Lighting  ",
        scenario=LoadScenario.NORMAL,
        phase_system=PhaseSystem.SINGLE_PHASE,
        connected_power_kw=Decimal("5"),
        utilized_power_kw=Decimal("4"),
        demand_power_kw=Decimal("3.6"),
        apparent_power_kva=Decimal("4"),
        reactive_power_kvar=Decimal("1.7436"),
        design_current_a=Decimal("17.3913"),
    )

    assert result.load_code == "LGT-001"
    assert result.load_name == "Office Lighting"


@pytest.mark.unit
def test_float_result_value_is_rejected() -> None:
    """Binary floating-point calculation outputs must not be accepted."""

    with pytest.raises(
        TypeError,
        match="connected_power_kw must be a Decimal",
    ):
        LoadCalculationResult(
            load_code="BAD-FLOAT",
            load_name="Invalid Float Result",
            scenario=LoadScenario.NORMAL,
            phase_system=PhaseSystem.THREE_PHASE,
            connected_power_kw=10.0,  # type: ignore[arg-type]
            utilized_power_kw=Decimal("8"),
            demand_power_kw=Decimal("7"),
            apparent_power_kva=Decimal("8"),
            reactive_power_kvar=Decimal("3"),
            design_current_a=Decimal("12"),
        )


@pytest.mark.unit
def test_negative_result_value_is_rejected() -> None:
    """Calculated electrical values must not be negative."""

    with pytest.raises(
        ValueError,
        match="demand_power_kw must not be negative",
    ):
        LoadCalculationResult(
            load_code="BAD-NEGATIVE",
            load_name="Negative Result",
            scenario=LoadScenario.NORMAL,
            phase_system=PhaseSystem.THREE_PHASE,
            connected_power_kw=Decimal("10"),
            utilized_power_kw=Decimal("8"),
            demand_power_kw=Decimal("-1"),
            apparent_power_kva=Decimal("8"),
            reactive_power_kvar=Decimal("3"),
            design_current_a=Decimal("12"),
        )


@pytest.mark.unit
def test_valid_status_must_not_contain_warnings() -> None:
    """VALID results cannot contain engineering warnings."""

    warning = CalculationWarning(
        code=LoadWarningCode.ZERO_DEMAND,
        message="Calculated demand is zero.",
    )

    with pytest.raises(
        ValueError,
        match="VALID result must not contain warnings",
    ):
        make_load_result(
            status=CalculationStatus.VALID,
            warnings=(warning,),
        )


@pytest.mark.unit
def test_warning_status_requires_warning_record() -> None:
    """WARNING results must contain at least one warning."""

    with pytest.raises(
        ValueError,
        match="WARNING result must contain at least one warning",
    ):
        make_load_result(
            status=CalculationStatus.WARNING,
            warnings=(),
        )


@pytest.mark.unit
def test_create_valid_group_result() -> None:
    """A load group result should preserve aggregated values."""

    load_result = make_load_result()

    group_result = LoadGroupCalculationResult(
        group_code="PUMP-GRP",
        group_name="Process Pumps",
        coincidence_factor=Decimal("0.90"),
        connected_power_kw=Decimal("32.6087"),
        pre_coincidence_demand_kw=Decimal("23.4783"),
        demand_power_kw=Decimal("21.1305"),
        apparent_power_kva=Decimal("24.8594"),
        reactive_power_kvar=Decimal("13.0842"),
        load_results=(load_result,),
    )

    assert group_result.group_code == "PUMP-GRP"
    assert group_result.coincidence_factor == Decimal("0.90")
    assert group_result.demand_power_kw == Decimal("21.1305")
    assert group_result.load_results == (load_result,)


@pytest.mark.unit
def test_empty_group_results_are_rejected() -> None:
    """An aggregated result must contain individual load results."""

    with pytest.raises(
        ValueError,
        match="load_results must not be empty",
    ):
        LoadGroupCalculationResult(
            group_code="EMPTY-GRP",
            group_name="Empty Group",
            coincidence_factor=Decimal("1"),
            connected_power_kw=Decimal("0"),
            pre_coincidence_demand_kw=Decimal("0"),
            demand_power_kw=Decimal("0"),
            apparent_power_kva=Decimal("0"),
            reactive_power_kvar=Decimal("0"),
            load_results=(),
        )


@pytest.mark.unit
def test_duplicate_load_result_codes_are_rejected() -> None:
    """A group cannot contain duplicate calculated load codes."""

    first_result = make_load_result(load_code="MTR-001")
    second_result = make_load_result(load_code="MTR-001")

    with pytest.raises(
        ValueError,
        match="load result codes must be unique",
    ):
        LoadGroupCalculationResult(
            group_code="DUPLICATE-GRP",
            group_name="Duplicate Group",
            coincidence_factor=Decimal("1"),
            connected_power_kw=Decimal("65.2174"),
            pre_coincidence_demand_kw=Decimal("46.9566"),
            demand_power_kw=Decimal("46.9566"),
            apparent_power_kva=Decimal("55.2430"),
            reactive_power_kvar=Decimal("29.0760"),
            load_results=(
                first_result,
                second_result,
            ),
        )


@pytest.mark.unit
def test_group_coincidence_above_one_is_rejected() -> None:
    """Coincidence factor cannot exceed unity."""

    with pytest.raises(
        ValueError,
        match="coincidence_factor must not be greater than 1",
    ):
        LoadGroupCalculationResult(
            group_code="BAD-CF",
            group_name="Invalid Coincidence",
            coincidence_factor=Decimal("1.01"),
            connected_power_kw=Decimal("10"),
            pre_coincidence_demand_kw=Decimal("8"),
            demand_power_kw=Decimal("8"),
            apparent_power_kva=Decimal("9"),
            reactive_power_kvar=Decimal("4"),
            load_results=(make_load_result(),),
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "warnings", "expected_message"),
    [
        (
            CalculationStatus.VALID,
            (
                CalculationWarning(
                    code=LoadWarningCode.ZERO_DEMAND,
                    message="Calculated demand is zero.",
                ),
            ),
            "VALID result must not contain warnings",
        ),
        (
            CalculationStatus.WARNING,
            (),
            "WARNING result must contain at least one warning",
        ),
        (
            CalculationStatus.WARNING,
            (
                CalculationWarning(
                    code=LoadWarningCode.COINCIDENCE_FACTOR_NOT_ESTABLISHED,
                    message="Group coincidence factor is not established.",
                ),
            ),
            "the status must be REVIEW_REQUIRED",
        ),
        (
            CalculationStatus.REVIEW_REQUIRED,
            (
                CalculationWarning(
                    code=LoadWarningCode.ZERO_DEMAND,
                    message="Calculated demand is zero.",
                ),
            ),
            "REVIEW_REQUIRED result must contain at least one not-established warning",
        ),
    ],
)
def test_group_status_and_warning_consistency(
    status: CalculationStatus,
    warnings: tuple[CalculationWarning, ...],
    expected_message: str,
) -> None:
    """Group status must remain consistent with warning records."""

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        LoadGroupCalculationResult(
            group_code="STATUS-GRP",
            group_name="Status Validation Group",
            coincidence_factor=Decimal("1"),
            connected_power_kw=Decimal("32.6087"),
            pre_coincidence_demand_kw=Decimal("23.4783"),
            demand_power_kw=Decimal("23.4783"),
            apparent_power_kva=Decimal("27.6215"),
            reactive_power_kvar=Decimal("14.5380"),
            load_results=(make_load_result(),),
            status=status,
            warnings=warnings,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("warning_codes", "expected_status"),
    [
        ((), CalculationStatus.VALID),
        (
            (LoadWarningCode.ZERO_DEMAND,),
            CalculationStatus.WARNING,
        ),
        (
            (LoadWarningCode.UTILIZATION_FACTOR_NOT_ESTABLISHED,),
            CalculationStatus.REVIEW_REQUIRED,
        ),
        (
            (
                LoadWarningCode.ZERO_DEMAND,
                LoadWarningCode.EFFICIENCY_NOT_ESTABLISHED,
            ),
            CalculationStatus.REVIEW_REQUIRED,
        ),
    ],
)
def test_resolve_status_precedence(
    warning_codes: tuple[LoadWarningCode, ...],
    expected_status: CalculationStatus,
) -> None:
    """A not-established factor outranks every other warning (A15)."""

    warnings = tuple(
        CalculationWarning(
            code=code,
            message=f"{code.value} message.",
        )
        for code in warning_codes
    )

    assert resolve_status(warnings) is expected_status


@pytest.mark.unit
def test_warning_status_rejects_a_not_established_warning() -> None:
    """A not-established factor may not be reported as a plain WARNING."""

    warning = CalculationWarning(
        code=LoadWarningCode.DEMAND_FACTOR_NOT_ESTABLISHED,
        message="Demand factor is not established.",
    )

    with pytest.raises(
        ValueError,
        match="the status must be REVIEW_REQUIRED",
    ):
        make_load_result(
            status=CalculationStatus.WARNING,
            warnings=(warning,),
        )


@pytest.mark.unit
def test_review_required_requires_a_not_established_warning() -> None:
    """REVIEW_REQUIRED without an unestablished factor is inconsistent."""

    warning = CalculationWarning(
        code=LoadWarningCode.ZERO_DEMAND,
        message="Calculated demand is zero.",
    )

    with pytest.raises(
        ValueError,
        match="REVIEW_REQUIRED result must contain at least one not-established warning",
    ):
        make_load_result(
            status=CalculationStatus.REVIEW_REQUIRED,
            warnings=(warning,),
        )


@pytest.mark.unit
def test_review_required_result_is_accepted() -> None:
    """A REVIEW_REQUIRED result carrying its not-established warning is valid."""

    warning = CalculationWarning(
        code=LoadWarningCode.UTILIZATION_FACTOR_NOT_ESTABLISHED,
        message="Utilization factor is not established.",
    )

    result = make_load_result(
        status=CalculationStatus.REVIEW_REQUIRED,
        warnings=(warning,),
    )

    assert result.status is CalculationStatus.REVIEW_REQUIRED
    assert result.warnings == (warning,)


@pytest.mark.unit
def test_group_result_declares_the_coincidence_assumption() -> None:
    """A15 (e): the group result states how coincidence was applied."""

    group_result = LoadGroupCalculationResult(
        group_code="PUMP-GRP",
        group_name="Process Pumps",
        coincidence_factor=Decimal("0.90"),
        connected_power_kw=Decimal("32.6087"),
        pre_coincidence_demand_kw=Decimal("23.4783"),
        demand_power_kw=Decimal("21.1305"),
        apparent_power_kva=Decimal("24.8594"),
        reactive_power_kvar=Decimal("13.0842"),
        load_results=(make_load_result(),),
    )

    assert GROUP_COINCIDENCE_ASSUMPTION in group_result.assumptions


@pytest.mark.unit
def test_group_blank_assumption_text_is_rejected() -> None:
    """A declared assumption must carry readable text."""

    with pytest.raises(
        ValueError,
        match="assumptions must contain non-empty text",
    ):
        LoadGroupCalculationResult(
            group_code="BLANK-ASSUMPTION",
            group_name="Blank Assumption Group",
            coincidence_factor=Decimal("1"),
            connected_power_kw=Decimal("10"),
            pre_coincidence_demand_kw=Decimal("8"),
            demand_power_kw=Decimal("8"),
            apparent_power_kva=Decimal("8"),
            reactive_power_kvar=Decimal("0"),
            load_results=(make_load_result(),),
            assumptions=("   ",),
        )
