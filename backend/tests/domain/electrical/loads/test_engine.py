"""
Unit and golden-reference tests for load and demand calculations.
KESE-S2-M1
"""

from decimal import Decimal

import pytest

from app.domain.electrical.loads.engine import (
    calculate_load,
    calculate_load_group,
)
from app.domain.electrical.loads.models import (
    LoadGroupInput,
    LoadInput,
    LoadScenario,
    PhaseSystem,
    PowerBasis,
)
from app.domain.electrical.loads.results import (
    GROUP_COINCIDENCE_ASSUMPTION,
    CalculationStatus,
    LoadWarningCode,
)


def make_motor_load(
    *,
    code: str = "MTR-001",
    power_factor: Decimal | None = Decimal("0.85"),
    efficiency: Decimal | None = Decimal("0.92"),
    utilization_factor: Decimal | None = Decimal("0.80"),
    demand_factor: Decimal | None = Decimal("0.90"),
) -> LoadInput:
    """Create the approved three-phase motor reference load."""

    return LoadInput(
        code=code,
        name="Process Water Pump",
        quantity=2,
        rated_power_kw=Decimal("15"),
        phase_system=PhaseSystem.THREE_PHASE,
        voltage_v=Decimal("415"),
        power_factor=power_factor,
        efficiency=efficiency,
        utilization_factor=utilization_factor,
        demand_factor=demand_factor,
        scenario=LoadScenario.NORMAL,
        power_basis=PowerBasis.MECHANICAL_OUTPUT,
    )


@pytest.mark.unit
@pytest.mark.golden
def test_three_phase_motor_reference_calculation() -> None:
    """Calculate the approved three-phase motor reference case."""

    result = calculate_load(make_motor_load())

    assert result.connected_power_kw == Decimal("32.6087")
    assert result.utilized_power_kw == Decimal("26.0870")
    assert result.demand_power_kw == Decimal("23.4783")
    assert result.apparent_power_kva == Decimal("27.6215")
    assert result.reactive_power_kvar == Decimal("14.5505")
    assert result.design_current_a == Decimal("38.4272")
    assert result.status is CalculationStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
@pytest.mark.golden
def test_single_phase_electrical_input_reference() -> None:
    """Calculate active, apparent, reactive power and current."""

    load = LoadInput(
        code="LGT-001",
        name="Office Lighting",
        quantity=2,
        rated_power_kw=Decimal("5"),
        phase_system=PhaseSystem.SINGLE_PHASE,
        voltage_v=Decimal("230"),
        power_factor=Decimal("0.90"),
        utilization_factor=Decimal("0.80"),
        demand_factor=Decimal("0.75"),
        power_basis=PowerBasis.ELECTRICAL_INPUT,
    )

    result = calculate_load(load)

    assert result.connected_power_kw == Decimal("10.0000")
    assert result.utilized_power_kw == Decimal("8.0000")
    assert result.demand_power_kw == Decimal("6.0000")
    assert result.apparent_power_kva == Decimal("6.6667")
    assert result.reactive_power_kvar == Decimal("2.9059")
    assert result.design_current_a == Decimal("28.9855")
    assert result.status is CalculationStatus.VALID


@pytest.mark.unit
@pytest.mark.golden
def test_dc_load_reference_calculation() -> None:
    """DC calculations should not produce reactive power."""

    load = LoadInput(
        code="DC-001",
        name="DC Control Load",
        quantity=2,
        rated_power_kw=Decimal("2.4"),
        phase_system=PhaseSystem.DC,
        voltage_v=Decimal("48"),
        power_factor=Decimal("1"),
        utilization_factor=Decimal("0.50"),
        demand_factor=Decimal("0.75"),
    )

    result = calculate_load(load)

    assert result.connected_power_kw == Decimal("4.8000")
    assert result.utilized_power_kw == Decimal("2.4000")
    assert result.demand_power_kw == Decimal("1.8000")
    assert result.apparent_power_kva == Decimal("1.8000")
    assert result.reactive_power_kvar == Decimal("0.0000")
    assert result.design_current_a == Decimal("37.5000")
    assert result.status is CalculationStatus.VALID


@pytest.mark.unit
def test_zero_demand_produces_warning() -> None:
    """A zero utilization or demand factor should produce a warning."""

    load = make_motor_load(
        utilization_factor=Decimal("0"),
    )

    result = calculate_load(load)

    assert result.connected_power_kw == Decimal("32.6087")
    assert result.utilized_power_kw == Decimal("0.0000")
    assert result.demand_power_kw == Decimal("0.0000")
    assert result.apparent_power_kva == Decimal("0.0000")
    assert result.reactive_power_kvar == Decimal("0.0000")
    assert result.design_current_a == Decimal("0.0000")
    assert result.status is CalculationStatus.WARNING
    assert result.warnings[0].code is LoadWarningCode.ZERO_DEMAND


@pytest.mark.unit
def test_low_power_factor_and_efficiency_no_longer_warn() -> None:
    """The unreferenced 0.80 limits are withdrawn (A15 (b), GAP-015)."""

    load = make_motor_load(
        power_factor=Decimal("0.50"),
        efficiency=Decimal("0.50"),
    )

    result = calculate_load(load)

    assert result.status is CalculationStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
def test_blank_utilization_factor_is_reported_as_not_established() -> None:
    """A blank utilization factor calculates with 1 and needs review."""

    established = calculate_load(
        make_motor_load(
            utilization_factor=Decimal("1"),
        )
    )

    result = calculate_load(
        make_motor_load(
            utilization_factor=None,
        )
    )

    assert result.status is CalculationStatus.REVIEW_REQUIRED
    assert [warning.code for warning in result.warnings] == [
        LoadWarningCode.UTILIZATION_FACTOR_NOT_ESTABLISHED
    ]
    assert result.utilized_power_kw == established.utilized_power_kw
    assert result.demand_power_kw == established.demand_power_kw
    assert result.design_current_a == established.design_current_a


@pytest.mark.unit
def test_blank_demand_factor_is_reported_as_not_established() -> None:
    """A blank demand factor calculates with 1 and needs review."""

    established = calculate_load(
        make_motor_load(
            demand_factor=Decimal("1"),
        )
    )

    result = calculate_load(
        make_motor_load(
            demand_factor=None,
        )
    )

    assert result.status is CalculationStatus.REVIEW_REQUIRED
    assert [warning.code for warning in result.warnings] == [
        LoadWarningCode.DEMAND_FACTOR_NOT_ESTABLISHED
    ]
    assert result.demand_power_kw == established.demand_power_kw


@pytest.mark.unit
def test_blank_efficiency_warns_only_for_mechanical_output() -> None:
    """Efficiency is used, and therefore required, only for shaft ratings."""

    mechanical_result = calculate_load(
        make_motor_load(
            efficiency=None,
        )
    )

    electrical_load = LoadInput(
        code="HTR-002",
        name="Electric Heater",
        quantity=1,
        rated_power_kw=Decimal("10"),
        phase_system=PhaseSystem.THREE_PHASE,
        voltage_v=Decimal("415"),
        power_factor=Decimal("1"),
        utilization_factor=Decimal("1"),
        demand_factor=Decimal("1"),
        power_basis=PowerBasis.ELECTRICAL_INPUT,
    )

    electrical_result = calculate_load(electrical_load)

    assert mechanical_result.status is CalculationStatus.REVIEW_REQUIRED
    assert [warning.code for warning in mechanical_result.warnings] == [
        LoadWarningCode.EFFICIENCY_NOT_ESTABLISHED
    ]
    assert mechanical_result.connected_power_kw == Decimal("30.0000")

    assert electrical_result.status is CalculationStatus.VALID
    assert electrical_result.warnings == ()


@pytest.mark.unit
def test_dc_load_without_power_factor_is_calculated_with_unity() -> None:
    """A DC load has no power factor and produces no warning for it."""

    load = LoadInput(
        code="DC-003",
        name="DC Control Load",
        quantity=2,
        rated_power_kw=Decimal("2.4"),
        phase_system=PhaseSystem.DC,
        voltage_v=Decimal("48"),
        utilization_factor=Decimal("0.50"),
        demand_factor=Decimal("0.75"),
    )

    result = calculate_load(load)

    assert result.apparent_power_kva == Decimal("1.8000")
    assert result.reactive_power_kvar == Decimal("0.0000")
    assert result.design_current_a == Decimal("37.5000")
    assert result.status is CalculationStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
def test_multiple_load_warnings_are_preserved() -> None:
    """One load may produce more than one controlled warning."""

    load = make_motor_load(
        utilization_factor=None,
        demand_factor=Decimal("0"),
    )

    result = calculate_load(load)

    warning_codes = {warning.code for warning in result.warnings}

    assert result.status is CalculationStatus.REVIEW_REQUIRED
    assert warning_codes == {
        LoadWarningCode.UTILIZATION_FACTOR_NOT_ESTABLISHED,
        LoadWarningCode.ZERO_DEMAND,
    }


@pytest.mark.unit
def test_electrical_input_efficiency_does_not_change_power() -> None:
    """Efficiency applies only to mechanical-output ratings."""

    load = LoadInput(
        code="HTR-001",
        name="Electric Heater",
        quantity=3,
        rated_power_kw=Decimal("10"),
        phase_system=PhaseSystem.THREE_PHASE,
        voltage_v=Decimal("415"),
        power_factor=Decimal("1"),
        efficiency=Decimal("0.70"),
        utilization_factor=Decimal("1"),
        demand_factor=Decimal("1"),
        power_basis=PowerBasis.ELECTRICAL_INPUT,
    )

    result = calculate_load(load)

    assert result.connected_power_kw == Decimal("30.0000")
    assert result.demand_power_kw == Decimal("30.0000")
    assert result.status is CalculationStatus.VALID


@pytest.mark.unit
@pytest.mark.golden
def test_load_group_vector_aggregation_reference() -> None:
    """Aggregate active and reactive power before calculating group kVA."""

    motor = LoadInput(
        code="LOAD-A",
        name="Three-phase Load",
        quantity=1,
        rated_power_kw=Decimal("10"),
        phase_system=PhaseSystem.THREE_PHASE,
        voltage_v=Decimal("415"),
        power_factor=Decimal("0.80"),
        utilization_factor=Decimal("1"),
        demand_factor=Decimal("1"),
    )

    lighting = LoadInput(
        code="LOAD-B",
        name="Single-phase Load",
        quantity=1,
        rated_power_kw=Decimal("5"),
        phase_system=PhaseSystem.SINGLE_PHASE,
        voltage_v=Decimal("230"),
        power_factor=Decimal("1"),
        utilization_factor=Decimal("0.50"),
        demand_factor=Decimal("1"),
    )

    group = LoadGroupInput(
        code="DB-001",
        name="Distribution Board Loads",
        loads=(motor, lighting),
        coincidence_factor=Decimal("0.80"),
    )

    result = calculate_load_group(group)

    assert result.connected_power_kw == Decimal("15.0000")
    assert result.pre_coincidence_demand_kw == Decimal("12.5000")
    assert result.demand_power_kw == Decimal("10.0000")
    assert result.reactive_power_kvar == Decimal("6.0000")
    assert result.apparent_power_kva == Decimal("11.6619")
    assert len(result.load_results) == 2
    assert result.status is CalculationStatus.VALID
    assert result.warnings == ()


@pytest.mark.unit
def test_group_coincidence_factor_is_applied_once() -> None:
    """Coincidence should be applied after individual demand calculation."""

    first_load = LoadInput(
        code="LOAD-01",
        name="Load One",
        quantity=1,
        rated_power_kw=Decimal("10"),
        phase_system=PhaseSystem.THREE_PHASE,
        voltage_v=Decimal("415"),
        power_factor=Decimal("1"),
        utilization_factor=Decimal("1"),
        demand_factor=Decimal("0.80"),
    )

    second_load = LoadInput(
        code="LOAD-02",
        name="Load Two",
        quantity=1,
        rated_power_kw=Decimal("20"),
        phase_system=PhaseSystem.THREE_PHASE,
        voltage_v=Decimal("415"),
        power_factor=Decimal("1"),
        utilization_factor=Decimal("1"),
        demand_factor=Decimal("0.50"),
    )

    group = LoadGroupInput(
        code="GROUP-01",
        name="Coincidence Test Group",
        loads=(first_load, second_load),
        coincidence_factor=Decimal("0.75"),
    )

    result = calculate_load_group(group)

    assert result.connected_power_kw == Decimal("30.0000")
    assert result.pre_coincidence_demand_kw == Decimal("18.0000")
    assert result.demand_power_kw == Decimal("13.5000")
    assert result.apparent_power_kva == Decimal("13.5000")
    assert result.reactive_power_kvar == Decimal("0.0000")


@pytest.mark.unit
def test_group_warnings_include_load_code() -> None:
    """Group warnings should identify the originating load."""

    blank_factor_load = make_motor_load(
        code="MTR-NO-UF",
        utilization_factor=None,
    )

    group = LoadGroupInput(
        code="WARNING-GRP",
        name="Warning Group",
        loads=(blank_factor_load,),
        coincidence_factor=Decimal("1"),
    )

    result = calculate_load_group(group)

    assert result.status is CalculationStatus.REVIEW_REQUIRED
    assert result.warnings[0].code is LoadWarningCode.UTILIZATION_FACTOR_NOT_ESTABLISHED
    assert result.warnings[0].message.startswith("MTR-NO-UF:")


@pytest.mark.unit
def test_blank_group_coincidence_is_reported_as_not_established() -> None:
    """A blank coincidence factor aggregates with 1 and needs review."""

    group = LoadGroupInput(
        code="BLANK-CF-GRP",
        name="Unestablished Coincidence Group",
        loads=(make_motor_load(),),
    )

    result = calculate_load_group(group)

    assert result.coincidence_factor == Decimal("1")
    assert result.pre_coincidence_demand_kw == Decimal("23.4783")
    assert result.demand_power_kw == Decimal("23.4783")
    assert result.status is CalculationStatus.REVIEW_REQUIRED
    assert [warning.code for warning in result.warnings] == [
        LoadWarningCode.COINCIDENCE_FACTOR_NOT_ESTABLISHED
    ]


@pytest.mark.unit
def test_group_is_review_required_when_one_member_is() -> None:
    """One unestablished member factor raises the whole group."""

    group = LoadGroupInput(
        code="MIXED-GRP",
        name="Mixed Group",
        loads=(
            make_motor_load(code="MTR-OK"),
            make_motor_load(
                code="MTR-NO-DF",
                demand_factor=None,
            ),
        ),
        coincidence_factor=Decimal("0.90"),
    )

    result = calculate_load_group(group)

    assert result.status is CalculationStatus.REVIEW_REQUIRED
    assert [warning.code for warning in result.warnings] == [
        LoadWarningCode.DEMAND_FACTOR_NOT_ESTABLISHED
    ]
    assert result.warnings[0].message.startswith("MTR-NO-DF:")


@pytest.mark.unit
def test_group_with_every_factor_established_is_valid() -> None:
    """A fully specified group carries no warning at all."""

    group = LoadGroupInput(
        code="CLEAN-GRP",
        name="Established Group",
        loads=(make_motor_load(),),
        coincidence_factor=Decimal("0.90"),
    )

    result = calculate_load_group(group)

    assert result.status is CalculationStatus.VALID
    assert result.warnings == ()
    assert result.assumptions == (GROUP_COINCIDENCE_ASSUMPTION,)


@pytest.mark.unit
def test_zero_group_coincidence_produces_zero_group_demand() -> None:
    """A permitted zero coincidence factor should zero group demand."""

    group = LoadGroupInput(
        code="STANDBY-GRP",
        name="Non-coincident Standby Group",
        loads=(make_motor_load(),),
        coincidence_factor=Decimal("0"),
    )

    result = calculate_load_group(group)

    assert result.pre_coincidence_demand_kw == Decimal("23.4783")
    assert result.demand_power_kw == Decimal("0.0000")
    assert result.apparent_power_kva == Decimal("0.0000")
    assert result.reactive_power_kvar == Decimal("0.0000")


@pytest.mark.unit
def test_calculate_load_rejects_wrong_input_type() -> None:
    """The engine should accept only validated LoadInput records."""

    with pytest.raises(
        TypeError,
        match="load must be a LoadInput record",
    ):
        calculate_load("invalid")  # type: ignore[arg-type]


@pytest.mark.unit
def test_calculate_group_rejects_wrong_input_type() -> None:
    """Group calculation should accept only LoadGroupInput records."""

    with pytest.raises(
        TypeError,
        match="group must be a LoadGroupInput record",
    ):
        calculate_load_group("invalid")  # type: ignore[arg-type]


@pytest.mark.unit
def test_scenario_is_preserved_in_result() -> None:
    """The result should retain the source operating scenario."""

    load = LoadInput(
        code="UPS-001",
        name="UPS Critical Load",
        quantity=1,
        rated_power_kw=Decimal("12"),
        phase_system=PhaseSystem.THREE_PHASE,
        voltage_v=Decimal("415"),
        power_factor=Decimal("0.90"),
        scenario=LoadScenario.UPS,
    )

    result = calculate_load(load)

    assert result.scenario is LoadScenario.UPS
