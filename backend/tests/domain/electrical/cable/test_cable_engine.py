"""
Unit tests for the cable sizing and ampacity engine.
KESE-S2-M13
"""

from decimal import Decimal

import pytest

from app.domain.electrical.cable.cable_engine import CableSizingEngine
from app.domain.electrical.cable.cable_models import (
    CableCircuitInput,
    CableConstruction,
    CableConstructionInput,
    CableInstallationInput,
    CableSizeSchedule,
    CableSizingInput,
    CircuitSystem,
    ConductorArrangement,
    ConductorMaterial,
    InstallationMethod,
    InsulationMaterial,
    ProtectiveConductorType,
)
from app.domain.electrical.cable.cable_results import (
    CableCheckStatus,
    CableSizingStatus,
    CableWarningCode,
)

STANDARD_PHASE_SIZES = tuple(
    Decimal(value) for value in ("35", "50", "70", "95", "120", "150", "185", "240", "300")
)


def make_circuit(**overrides: object) -> CableCircuitInput:
    values: dict[str, object] = {
        "design_current_a": Decimal("400"),
        "nominal_voltage_v": Decimal("415"),
        "route_length_m": Decimal("120"),
        "system": CircuitSystem.THREE_PHASE_FOUR_WIRE,
        "power_factor": Decimal("0.90"),
        "allowable_voltage_drop_percent": Decimal("3"),
        "fault_current_ka": Decimal("25"),
        "fault_duration_s": Decimal("1"),
        "harmonic_neutral_factor": Decimal("1"),
    }
    values.update(overrides)
    return CableCircuitInput(**values)


def make_construction(**overrides: object) -> CableConstructionInput:
    values: dict[str, object] = {
        "conductor_material": ConductorMaterial.COPPER,
        "insulation_material": InsulationMaterial.XLPE,
        "construction": CableConstruction.MULTICORE,
        "arrangement": ConductorArrangement.MULTICORE,
        "number_of_loaded_conductors": 3,
        "parallel_runs": 2,
        "neutral_required": True,
        "protective_conductor_type": ProtectiveConductorType.INTEGRAL_CORE,
    }
    values.update(overrides)
    return CableConstructionInput(**values)


def make_installation(**overrides: object) -> CableInstallationInput:
    values: dict[str, object] = {
        "method": InstallationMethod.CABLE_LADDER,
        "ambient_temperature_c": Decimal("45"),
        "ambient_derating_factor": Decimal("0.87"),
        "grouping_derating_factor": Decimal("0.80"),
        "grouped_circuits": 3,
    }
    values.update(overrides)
    return CableInstallationInput(**values)


def make_schedule(**overrides: object) -> CableSizeSchedule:
    values: dict[str, object] = {
        "phase_sizes_mm2": STANDARD_PHASE_SIZES,
        "neutral_sizes_mm2": STANDARD_PHASE_SIZES,
        "protective_sizes_mm2": tuple(
            Decimal(value) for value in ("16", "25", "35", "50", "70", "95", "120", "150")
        ),
    }
    values.update(overrides)
    return CableSizeSchedule(**values)


def make_study(**overrides: object) -> CableSizingInput:
    values: dict[str, object] = {
        "code": "CBL-FDR-01",
        "name": "Main LT Feeder Cable",
        "circuit": make_circuit(),
        "cable": make_construction(),
        "installation": make_installation(),
        "size_schedule": make_schedule(),
    }
    values.update(overrides)
    return CableSizingInput(**values)


@pytest.mark.unit
def test_selects_smallest_fully_compliant_standard_size() -> None:
    result = CableSizingEngine.calculate(make_study())

    assert result.status is CableSizingStatus.COMPLIANT
    assert result.conductor is not None
    assert result.conductor.phase_area_mm2 == Decimal("150")
    assert result.conductor.neutral_area_mm2 == Decimal("150")
    assert result.conductor.protective_area_mm2 == Decimal("95")
    assert result.governing_criterion == "AMPACITY"


@pytest.mark.unit
def test_calculates_expected_ampacity_result() -> None:
    result = CableSizingEngine.calculate(make_study())

    assert result.ampacity is not None
    assert result.ampacity.tabulated_ampacity_a_per_run == Decimal("302.4315")
    assert result.ampacity.combined_derating_factor == Decimal("0.6960")
    assert result.ampacity.total_installed_ampacity_a == Decimal("420.9846")
    assert result.ampacity.status is CableCheckStatus.PASS


@pytest.mark.unit
def test_calculates_expected_three_phase_voltage_drop() -> None:
    result = CableSizingEngine.calculate(make_study())

    assert result.voltage_drop is not None
    assert result.voltage_drop.resistance_ohm_per_km == Decimal("0.0733")
    assert result.voltage_drop.voltage_drop_v == Decimal("6.8421")
    assert result.voltage_drop.voltage_drop_percent == Decimal("1.6487")
    assert result.voltage_drop.status is CableCheckStatus.PASS


@pytest.mark.unit
def test_short_circuit_check_uses_current_per_parallel_run() -> None:
    result = CableSizingEngine.calculate(make_study())

    assert result.short_circuit is not None
    assert result.short_circuit.material_constant_k == Decimal("143")
    assert result.short_circuit.required_area_mm2 == Decimal("87.4126")
    assert result.short_circuit.withstand_current_ka == Decimal("42.9000")
    assert result.short_circuit.status is CableCheckStatus.PASS


@pytest.mark.unit
def test_short_circuit_duty_can_govern_selection() -> None:
    result = CableSizingEngine.calculate(
        make_study(
            circuit=make_circuit(
                design_current_a=Decimal("100"),
                fault_current_ka=Decimal("25"),
            ),
            cable=make_construction(parallel_runs=1),
        )
    )

    assert result.conductor is not None
    assert result.conductor.phase_area_mm2 == Decimal("185")
    assert result.governing_criterion == "SHORT_CIRCUIT_WITHSTAND"


@pytest.mark.unit
def test_missing_fault_duty_returns_not_applicable_short_circuit_check() -> None:
    result = CableSizingEngine.calculate(
        make_study(
            circuit=make_circuit(
                fault_current_ka=None,
                fault_duration_s=None,
            )
        )
    )

    assert result.short_circuit is not None
    assert result.short_circuit.status is CableCheckStatus.NOT_APPLICABLE
    assert result.short_circuit.required_area_mm2 is None


@pytest.mark.unit
def test_parallel_runs_emit_current_sharing_warning() -> None:
    result = CableSizingEngine.calculate(make_study())
    warning_codes = {warning.code for warning in result.warnings}

    assert CableWarningCode.PARALLEL_CABLE_CURRENT_SHARING in warning_codes


@pytest.mark.unit
def test_high_combined_derating_emits_warning() -> None:
    result = CableSizingEngine.calculate(make_study())
    warning_codes = {warning.code for warning in result.warnings}

    assert CableWarningCode.HIGH_TOTAL_DERATING in warning_codes


@pytest.mark.unit
def test_buried_cable_without_soil_value_emits_warning() -> None:
    result = CableSizingEngine.calculate(
        make_study(
            installation=make_installation(method=InstallationMethod.D2_DIRECT_BURIED),
        )
    )
    warning_codes = {warning.code for warning in result.warnings}

    assert CableWarningCode.SOIL_DATA_REQUIRED in warning_codes


@pytest.mark.unit
def test_confirmed_soil_value_suppresses_soil_warning() -> None:
    result = CableSizingEngine.calculate(
        make_study(
            installation=make_installation(
                method=InstallationMethod.D2_DIRECT_BURIED,
                burial_depth_m=Decimal("0.8"),
                soil_thermal_resistivity_k_m_per_w=Decimal("2.5"),
            ),
        )
    )
    warning_codes = {warning.code for warning in result.warnings}

    assert CableWarningCode.SOIL_DATA_REQUIRED not in warning_codes


@pytest.mark.unit
def test_metallic_armour_protective_path_is_not_applicable() -> None:
    result = CableSizingEngine.calculate(
        make_study(
            cable=make_construction(
                protective_conductor_type=ProtectiveConductorType.METALLIC_ARMOUR,
            )
        )
    )

    assert result.conductor is not None
    assert result.conductor.protective_area_mm2 is None
    assert result.conductor.protective_status is CableCheckStatus.NOT_APPLICABLE


@pytest.mark.unit
def test_reduced_neutral_selects_next_approved_half_size() -> None:
    result = CableSizingEngine.calculate(
        make_study(
            cable=make_construction(reduced_neutral_permitted=True),
        )
    )

    assert result.conductor is not None
    assert result.conductor.phase_area_mm2 == Decimal("150")
    assert result.conductor.neutral_area_mm2 == Decimal("95")


@pytest.mark.unit
def test_no_approved_size_returns_structured_result() -> None:
    result = CableSizingEngine.calculate(
        make_study(
            circuit=make_circuit(design_current_a=Decimal("2000")),
            size_schedule=make_schedule(
                phase_sizes_mm2=(Decimal("35"), Decimal("50")),
                neutral_sizes_mm2=(Decimal("35"), Decimal("50")),
                protective_sizes_mm2=(Decimal("16"), Decimal("25")),
            ),
        )
    )

    assert result.status is CableSizingStatus.NO_STANDARD_SIZE_AVAILABLE
    assert result.conductor is None
    assert result.ampacity is None
    assert result.warnings[-1].code is CableWarningCode.NO_STANDARD_SIZE_AVAILABLE


@pytest.mark.unit
def test_long_route_with_strict_limit_can_exhaust_size_schedule() -> None:
    result = CableSizingEngine.calculate(
        make_study(
            circuit=make_circuit(
                route_length_m=Decimal("1000"),
                allowable_voltage_drop_percent=Decimal("1"),
            )
        )
    )

    assert result.status is CableSizingStatus.NO_STANDARD_SIZE_AVAILABLE


@pytest.mark.unit
def test_aluminium_requires_larger_phase_conductor_than_copper() -> None:
    copper = CableSizingEngine.calculate(make_study())
    aluminium = CableSizingEngine.calculate(
        make_study(
            cable=make_construction(conductor_material=ConductorMaterial.ALUMINIUM),
        )
    )

    assert copper.conductor is not None
    assert aluminium.conductor is not None
    assert aluminium.conductor.phase_area_mm2 > copper.conductor.phase_area_mm2


@pytest.mark.unit
def test_invalid_study_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="study must be a CableSizingInput"):
        CableSizingEngine.calculate("invalid")
