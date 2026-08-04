"""
Unit tests for cable sizing and ampacity domain models.
KESE-S2-M13
"""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

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
        "reduced_neutral_permitted": False,
        "protective_conductor_type": ProtectiveConductorType.INTEGRAL_CORE,
        "armoured": True,
    }
    values.update(overrides)
    return CableConstructionInput(**values)


def make_installation(**overrides: object) -> CableInstallationInput:
    values: dict[str, object] = {
        "method": InstallationMethod.CABLE_LADDER,
        "ambient_temperature_c": Decimal("45"),
        "ambient_derating_factor": Decimal("0.87"),
        "grouping_derating_factor": Decimal("0.80"),
        "thermal_insulation_factor": Decimal("1"),
        "depth_derating_factor": Decimal("1"),
        "soil_thermal_resistivity_factor": Decimal("1"),
        "grouped_circuits": 3,
    }
    values.update(overrides)
    return CableInstallationInput(**values)


def make_schedule(**overrides: object) -> CableSizeSchedule:
    values: dict[str, object] = {
        "phase_sizes_mm2": (
            Decimal("35"),
            Decimal("50"),
            Decimal("70"),
            Decimal("95"),
            Decimal("120"),
            Decimal("150"),
            Decimal("185"),
            Decimal("240"),
            Decimal("300"),
        ),
        "neutral_sizes_mm2": (
            Decimal("35"),
            Decimal("50"),
            Decimal("70"),
            Decimal("95"),
            Decimal("120"),
            Decimal("150"),
        ),
        "protective_sizes_mm2": (
            Decimal("16"),
            Decimal("25"),
            Decimal("35"),
            Decimal("50"),
            Decimal("70"),
            Decimal("95"),
            Decimal("120"),
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
        "standard_reference": "IEC 60364-5-52",
        "ampacity_reference": "IEC 60287",
        "notes": "Critical feeder",
    }
    values.update(overrides)
    return CableSizingInput(**values)


@pytest.mark.unit
def test_create_valid_cable_sizing_study() -> None:
    study = make_study()

    assert study.code == "CBL-FDR-01"
    assert study.circuit.design_current_a == Decimal("400")
    assert study.cable.parallel_runs == 2
    assert study.installation.method is InstallationMethod.CABLE_LADDER
    assert study.size_schedule.phase_sizes_mm2[-1] == Decimal("300")


@pytest.mark.unit
def test_models_are_immutable() -> None:
    circuit = make_circuit()

    with pytest.raises(FrozenInstanceError):
        circuit.design_current_a = Decimal("500")


@pytest.mark.unit
def test_study_text_is_normalized() -> None:
    study = make_study(
        code="  CBL-FDR-01  ",
        name="  Main LT Feeder Cable  ",
        notes="  Critical feeder  ",
    )

    assert study.code == "CBL-FDR-01"
    assert study.name == "Main LT Feeder Cable"
    assert study.notes == "Critical feeder"


@pytest.mark.unit
def test_fault_current_and_duration_must_be_provided_together() -> None:
    with pytest.raises(ValueError, match="must be provided together"):
        make_circuit(fault_duration_s=None)


@pytest.mark.unit
def test_float_design_current_is_rejected() -> None:
    with pytest.raises(TypeError, match="design_current_a must be a Decimal"):
        make_circuit(design_current_a=400.0)


@pytest.mark.unit
def test_voltage_drop_limit_cannot_exceed_100_percent() -> None:
    with pytest.raises(ValueError, match="must not exceed 100"):
        make_circuit(allowable_voltage_drop_percent=Decimal("101"))


@pytest.mark.unit
def test_invalid_circuit_system_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="system must be a CircuitSystem"):
        make_circuit(system="THREE_PHASE_FOUR_WIRE")


@pytest.mark.unit
def test_multicore_cable_requires_multicore_arrangement() -> None:
    with pytest.raises(ValueError, match="requires MULTICORE arrangement"):
        make_construction(arrangement=ConductorArrangement.TREFOIL_TOUCHING)


@pytest.mark.unit
def test_single_core_cable_rejects_multicore_arrangement() -> None:
    with pytest.raises(ValueError, match="requires a single-core arrangement"):
        make_construction(
            construction=CableConstruction.SINGLE_CORE,
            arrangement=ConductorArrangement.MULTICORE,
        )


@pytest.mark.unit
def test_parallel_runs_must_be_positive_integer() -> None:
    with pytest.raises(ValueError, match="parallel_runs must be at least 1"):
        make_construction(parallel_runs=0)

    with pytest.raises(TypeError, match="parallel_runs must be an integer"):
        make_construction(parallel_runs=True)


@pytest.mark.unit
def test_reduced_neutral_requires_neutral_conductor() -> None:
    with pytest.raises(ValueError, match="requires neutral_required"):
        make_construction(
            neutral_required=False,
            reduced_neutral_permitted=True,
        )


@pytest.mark.unit
def test_combined_derating_factor_is_exact_decimal_product() -> None:
    installation = make_installation()

    assert installation.combined_derating_factor == Decimal("0.6960")


@pytest.mark.unit
def test_derating_factor_above_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="not greater than 1"):
        make_installation(ambient_derating_factor=Decimal("1.01"))


@pytest.mark.unit
def test_grouped_circuits_must_be_positive_integer() -> None:
    with pytest.raises(ValueError, match="grouped_circuits must be at least 1"):
        make_installation(grouped_circuits=0)

    with pytest.raises(TypeError, match="grouped_circuits must be an integer"):
        make_installation(grouped_circuits=True)


@pytest.mark.unit
def test_soil_data_requires_buried_installation_method() -> None:
    with pytest.raises(ValueError, match="require a D1 or D2"):
        make_installation(
            soil_thermal_resistivity_k_m_per_w=Decimal("2.5"),
        )


@pytest.mark.unit
def test_buried_installation_accepts_soil_data() -> None:
    installation = make_installation(
        method=InstallationMethod.D2_DIRECT_BURIED,
        burial_depth_m=Decimal("0.8"),
        soil_thermal_resistivity_k_m_per_w=Decimal("2.5"),
    )

    assert installation.burial_depth_m == Decimal("0.8")
    assert installation.soil_thermal_resistivity_k_m_per_w == Decimal("2.5")


@pytest.mark.unit
def test_phase_size_schedule_must_be_unique_and_ascending() -> None:
    with pytest.raises(ValueError, match="phase sizes must be unique"):
        make_schedule(
            phase_sizes_mm2=(Decimal("35"), Decimal("35")),
        )

    with pytest.raises(ValueError, match="phase sizes must be in ascending order"):
        make_schedule(
            phase_sizes_mm2=(Decimal("50"), Decimal("35")),
        )


@pytest.mark.unit
def test_three_wire_system_rejects_neutral_requirement() -> None:
    with pytest.raises(ValueError, match="cannot require a neutral conductor"):
        make_study(
            circuit=make_circuit(system=CircuitSystem.THREE_PHASE_THREE_WIRE),
        )


@pytest.mark.unit
def test_four_wire_system_requires_neutral_conductor() -> None:
    with pytest.raises(ValueError, match="requires a neutral conductor"):
        make_study(
            cable=make_construction(neutral_required=False),
        )


@pytest.mark.unit
def test_harmonic_loading_rejects_reduced_neutral() -> None:
    with pytest.raises(ValueError, match="reduced neutral is not permitted"):
        make_study(
            circuit=make_circuit(harmonic_neutral_factor=Decimal("1.25")),
            cable=make_construction(reduced_neutral_permitted=True),
        )
