"""
Cable sizing, voltage-drop, and short-circuit engineering engine.
KESE-S2-M13
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar

from app.domain.electrical.cable.cable_models import (
    CableConstruction,
    CableSizingInput,
    CircuitSystem,
    ConductorArrangement,
    ConductorMaterial,
    InstallationMethod,
    InsulationMaterial,
    ProtectiveConductorType,
)
from app.domain.electrical.cable.cable_results import (
    CableAmpacityResult,
    CableCheckStatus,
    CableConductorSizingResult,
    CableEngineeringWarning,
    CableShortCircuitResult,
    CableSizingResult,
    CableSizingStatus,
    CableVoltageDropResult,
    CableWarningCode,
)


class CableSizingEngine:
    """Deterministic IEC-oriented cable sizing engine."""

    _FOUR_PLACES = Decimal("0.0001")

    _RESISTIVITY_OHM_MM2_PER_M: ClassVar[dict[ConductorMaterial, Decimal]] = {
        ConductorMaterial.COPPER: Decimal("0.017241"),
        ConductorMaterial.ALUMINIUM: Decimal("0.028264"),
    }
    _TEMPERATURE_COEFFICIENT_PER_C: ClassVar[dict[ConductorMaterial, Decimal]] = {
        ConductorMaterial.COPPER: Decimal("0.00393"),
        ConductorMaterial.ALUMINIUM: Decimal("0.00403"),
    }
    _MAXIMUM_CONDUCTOR_TEMPERATURE_C: ClassVar[dict[InsulationMaterial, Decimal]] = {
        InsulationMaterial.PVC: Decimal("70"),
        InsulationMaterial.XLPE: Decimal("90"),
        InsulationMaterial.EPR: Decimal("90"),
        InsulationMaterial.MINERAL: Decimal("105"),
    }
    _ADIABATIC_K: ClassVar[dict[tuple[ConductorMaterial, InsulationMaterial], Decimal]] = {
        (ConductorMaterial.COPPER, InsulationMaterial.PVC): Decimal("115"),
        (ConductorMaterial.COPPER, InsulationMaterial.XLPE): Decimal("143"),
        (ConductorMaterial.COPPER, InsulationMaterial.EPR): Decimal("143"),
        (ConductorMaterial.COPPER, InsulationMaterial.MINERAL): Decimal("176"),
        (ConductorMaterial.ALUMINIUM, InsulationMaterial.PVC): Decimal("76"),
        (ConductorMaterial.ALUMINIUM, InsulationMaterial.XLPE): Decimal("94"),
        (ConductorMaterial.ALUMINIUM, InsulationMaterial.EPR): Decimal("94"),
        (ConductorMaterial.ALUMINIUM, InsulationMaterial.MINERAL): Decimal("116"),
    }

    # Coefficients produce a conservative reference ampacity in amperes from
    # coefficient * area_mm2 ** 0.75 before independently supplied derating.
    _MATERIAL_AMPACITY_COEFFICIENT: ClassVar[dict[ConductorMaterial, Decimal]] = {
        ConductorMaterial.COPPER: Decimal("8.00"),
        ConductorMaterial.ALUMINIUM: Decimal("6.30"),
    }
    _INSULATION_AMPACITY_FACTOR: ClassVar[dict[InsulationMaterial, Decimal]] = {
        InsulationMaterial.PVC: Decimal("0.85"),
        InsulationMaterial.XLPE: Decimal("1.00"),
        InsulationMaterial.EPR: Decimal("1.00"),
        InsulationMaterial.MINERAL: Decimal("1.05"),
    }
    _INSTALLATION_AMPACITY_FACTOR: ClassVar[dict[InstallationMethod, Decimal]] = {
        InstallationMethod.A1_INSULATED_WALL_CONDUIT: Decimal("0.63"),
        InstallationMethod.A2_INSULATED_WALL_MULTICORE: Decimal("0.60"),
        InstallationMethod.B1_WALL_CONDUIT_SINGLE_CORE: Decimal("0.75"),
        InstallationMethod.B2_WALL_CONDUIT_MULTICORE: Decimal("0.70"),
        InstallationMethod.C_CLIPPED_DIRECT: Decimal("0.88"),
        InstallationMethod.D1_GROUND_DUCT: Decimal("0.72"),
        InstallationMethod.D2_DIRECT_BURIED: Decimal("0.78"),
        InstallationMethod.E_FREE_AIR_MULTICORE: Decimal("0.95"),
        InstallationMethod.F_FREE_AIR_TOUCHING_SINGLE_CORE: Decimal("1.00"),
        InstallationMethod.G_FREE_AIR_SPACED_SINGLE_CORE: Decimal("1.08"),
        InstallationMethod.CABLE_TRAY: Decimal("0.92"),
        InstallationMethod.CABLE_LADDER: Decimal("0.98"),
        InstallationMethod.ENGINEERED_IEC_60287: Decimal("1.00"),
    }
    _CONSTRUCTION_AMPACITY_FACTOR: ClassVar[dict[CableConstruction, Decimal]] = {
        CableConstruction.SINGLE_CORE: Decimal("1.00"),
        CableConstruction.MULTICORE: Decimal("0.90"),
    }
    _ARRANGEMENT_REACTANCE_OHM_PER_KM: ClassVar[dict[ConductorArrangement, Decimal]] = {
        ConductorArrangement.MULTICORE: Decimal("0.075"),
        ConductorArrangement.FLAT_TOUCHING: Decimal("0.085"),
        ConductorArrangement.FLAT_SPACED: Decimal("0.095"),
        ConductorArrangement.TREFOIL_TOUCHING: Decimal("0.080"),
        ConductorArrangement.TREFOIL_SPACED: Decimal("0.090"),
    }

    @classmethod
    def calculate(cls, study: CableSizingInput) -> CableSizingResult:
        """Select the smallest approved cable size satisfying every check."""

        if not isinstance(study, CableSizingInput):
            raise TypeError("study must be a CableSizingInput record")

        base_warnings = cls._installation_warnings(study)

        for phase_area_mm2 in study.size_schedule.phase_sizes_mm2:
            conductor = cls._calculate_conductor_sizes(study, phase_area_mm2)
            if conductor is None:
                continue

            ampacity = cls._calculate_ampacity(study, phase_area_mm2)
            voltage_drop = cls._calculate_voltage_drop(study, phase_area_mm2)
            short_circuit = cls._calculate_short_circuit(study, phase_area_mm2)

            check_statuses = (
                conductor.neutral_status,
                conductor.protective_status,
                ampacity.status,
                voltage_drop.status,
                short_circuit.status,
            )
            if CableCheckStatus.FAIL in check_statuses:
                continue

            warnings = cls._deduplicate_warnings(
                base_warnings + cls._selection_warnings(study, ampacity)
            )
            return CableSizingResult(
                study_code=study.code,
                status=CableSizingStatus.COMPLIANT,
                conductor=conductor,
                ampacity=ampacity,
                voltage_drop=voltage_drop,
                short_circuit=short_circuit,
                warnings=warnings,
                governing_criterion=cls._governing_criterion(
                    ampacity,
                    voltage_drop,
                    short_circuit,
                ),
                standard_reference=study.standard_reference,
                ampacity_reference=study.ampacity_reference,
            )

        warning = CableEngineeringWarning(
            code=CableWarningCode.NO_STANDARD_SIZE_AVAILABLE,
            message="No approved standard cable size satisfies all design checks",
            field_name="phase_sizes_mm2",
        )
        return CableSizingResult(
            study_code=study.code,
            status=CableSizingStatus.NO_STANDARD_SIZE_AVAILABLE,
            conductor=None,
            ampacity=None,
            voltage_drop=None,
            short_circuit=None,
            warnings=cls._deduplicate_warnings((*base_warnings, warning)),
            standard_reference=study.standard_reference,
            ampacity_reference=study.ampacity_reference,
        )

    @classmethod
    def _calculate_ampacity(
        cls,
        study: CableSizingInput,
        phase_area_mm2: Decimal,
    ) -> CableAmpacityResult:
        area_power = phase_area_mm2.sqrt() * phase_area_mm2.sqrt().sqrt()
        tabulated_ampacity = (
            cls._MATERIAL_AMPACITY_COEFFICIENT[study.cable.conductor_material]
            * cls._INSULATION_AMPACITY_FACTOR[study.cable.insulation_material]
            * cls._INSTALLATION_AMPACITY_FACTOR[study.installation.method]
            * cls._CONSTRUCTION_AMPACITY_FACTOR[study.cable.construction]
            * area_power
        )
        combined_factor = study.installation.combined_derating_factor
        derated_per_run = tabulated_ampacity * combined_factor
        total_ampacity = derated_per_run * Decimal(study.cable.parallel_runs)
        required_tabulated = (
            study.circuit.design_current_a / Decimal(study.cable.parallel_runs) / combined_factor
        )
        utilization = study.circuit.design_current_a / total_ampacity
        status = (
            CableCheckStatus.PASS
            if total_ampacity >= study.circuit.design_current_a
            else CableCheckStatus.FAIL
        )
        return CableAmpacityResult(
            tabulated_ampacity_a_per_run=cls._round(tabulated_ampacity),
            combined_derating_factor=combined_factor,
            derated_ampacity_a_per_run=cls._round(derated_per_run),
            parallel_runs=study.cable.parallel_runs,
            total_installed_ampacity_a=cls._round(total_ampacity),
            design_current_a=study.circuit.design_current_a,
            required_tabulated_ampacity_a_per_run=cls._round(required_tabulated),
            utilization_ratio=cls._round(utilization),
            status=status,
        )

    @classmethod
    def _calculate_voltage_drop(
        cls,
        study: CableSizingInput,
        phase_area_mm2: Decimal,
    ) -> CableVoltageDropResult:
        material = study.cable.conductor_material
        conductor_temperature_c = cls._MAXIMUM_CONDUCTOR_TEMPERATURE_C[
            study.cable.insulation_material
        ]
        resistance_20_c = (
            cls._RESISTIVITY_OHM_MM2_PER_M[material] * Decimal("1000") / phase_area_mm2
        )
        resistance_at_temperature = resistance_20_c * (
            Decimal("1")
            + cls._TEMPERATURE_COEFFICIENT_PER_C[material]
            * (conductor_temperature_c - Decimal("20"))
        )
        resistance = resistance_at_temperature / Decimal(study.cable.parallel_runs)
        reactance = cls._ARRANGEMENT_REACTANCE_OHM_PER_KM[study.cable.arrangement] / Decimal(
            study.cable.parallel_runs
        )
        power_factor = study.circuit.power_factor
        reactive_factor = (Decimal("1") - power_factor * power_factor).sqrt()
        impedance_component = resistance * power_factor + reactance * reactive_factor
        route_length_km = study.circuit.route_length_m / Decimal("1000")

        if study.circuit.system in {
            CircuitSystem.THREE_PHASE_THREE_WIRE,
            CircuitSystem.THREE_PHASE_FOUR_WIRE,
        }:
            circuit_factor = Decimal("3").sqrt()
        else:
            circuit_factor = Decimal("2")

        voltage_drop_v = (
            circuit_factor * study.circuit.design_current_a * route_length_km * impedance_component
        )
        voltage_drop_percent = voltage_drop_v / study.circuit.nominal_voltage_v * Decimal("100")
        status = (
            CableCheckStatus.PASS
            if voltage_drop_percent <= study.circuit.allowable_voltage_drop_percent
            else CableCheckStatus.FAIL
        )
        return CableVoltageDropResult(
            resistance_ohm_per_km=cls._round(resistance),
            reactance_ohm_per_km=cls._round(reactance),
            voltage_drop_v=cls._round(voltage_drop_v),
            voltage_drop_percent=cls._round(voltage_drop_percent),
            allowable_voltage_drop_percent=study.circuit.allowable_voltage_drop_percent,
            status=status,
        )

    @classmethod
    def _calculate_short_circuit(
        cls,
        study: CableSizingInput,
        phase_area_mm2: Decimal,
    ) -> CableShortCircuitResult:
        fault_current_ka = study.circuit.fault_current_ka
        fault_duration_s = study.circuit.fault_duration_s
        if fault_current_ka is None or fault_duration_s is None:
            return CableShortCircuitResult(
                fault_current_ka=None,
                fault_duration_s=None,
                material_constant_k=None,
                required_area_mm2=None,
                selected_area_mm2=phase_area_mm2,
                withstand_current_ka=None,
                status=CableCheckStatus.NOT_APPLICABLE,
            )

        material_constant = cls._ADIABATIC_K[
            (study.cable.conductor_material, study.cable.insulation_material)
        ]
        current_per_run_a = fault_current_ka * Decimal("1000") / Decimal(study.cable.parallel_runs)
        required_area = current_per_run_a * fault_duration_s.sqrt() / material_constant
        withstand_current_ka = (
            material_constant
            * phase_area_mm2
            * Decimal(study.cable.parallel_runs)
            / fault_duration_s.sqrt()
            / Decimal("1000")
        )
        status = CableCheckStatus.PASS if phase_area_mm2 >= required_area else CableCheckStatus.FAIL
        return CableShortCircuitResult(
            fault_current_ka=fault_current_ka,
            fault_duration_s=fault_duration_s,
            material_constant_k=material_constant,
            required_area_mm2=cls._round(required_area),
            selected_area_mm2=phase_area_mm2,
            withstand_current_ka=cls._round(withstand_current_ka),
            status=status,
        )

    @classmethod
    def _calculate_conductor_sizes(
        cls,
        study: CableSizingInput,
        phase_area_mm2: Decimal,
    ) -> CableConductorSizingResult | None:
        neutral_area: Decimal | None
        neutral_status: CableCheckStatus
        if study.cable.neutral_required:
            neutral_multiplier = study.circuit.harmonic_neutral_factor
            if study.cable.reduced_neutral_permitted:
                neutral_multiplier = min(neutral_multiplier, Decimal("0.50"))
            required_neutral_area = phase_area_mm2 * neutral_multiplier
            neutral_schedule = (
                study.size_schedule.neutral_sizes_mm2 or study.size_schedule.phase_sizes_mm2
            )
            neutral_area = cls._select_size(required_neutral_area, neutral_schedule)
            if neutral_area is None:
                return None
            neutral_status = CableCheckStatus.PASS
        else:
            neutral_area = None
            neutral_status = CableCheckStatus.NOT_APPLICABLE

        protective_area: Decimal | None
        protective_status: CableCheckStatus
        if study.cable.protective_conductor_type in {
            ProtectiveConductorType.INTEGRAL_CORE,
            ProtectiveConductorType.SEPARATE_INSULATED,
            ProtectiveConductorType.SEPARATE_BARE,
        }:
            required_protective_area = cls._required_protective_area(phase_area_mm2)
            protective_schedule = (
                study.size_schedule.protective_sizes_mm2 or study.size_schedule.phase_sizes_mm2
            )
            protective_area = cls._select_size(required_protective_area, protective_schedule)
            if protective_area is None:
                return None
            protective_status = CableCheckStatus.PASS
        else:
            protective_area = None
            protective_status = CableCheckStatus.NOT_APPLICABLE

        return CableConductorSizingResult(
            phase_area_mm2=phase_area_mm2,
            neutral_area_mm2=neutral_area,
            protective_area_mm2=protective_area,
            parallel_runs=study.cable.parallel_runs,
            phase_conductors_per_run=study.cable.number_of_loaded_conductors,
            neutral_status=neutral_status,
            protective_status=protective_status,
        )

    @staticmethod
    def _required_protective_area(phase_area_mm2: Decimal) -> Decimal:
        if phase_area_mm2 <= Decimal("16"):
            return phase_area_mm2
        if phase_area_mm2 <= Decimal("35"):
            return Decimal("16")
        return phase_area_mm2 / Decimal("2")

    @staticmethod
    def _select_size(
        required_area_mm2: Decimal,
        schedule: tuple[Decimal, ...],
    ) -> Decimal | None:
        return next((size for size in schedule if size >= required_area_mm2), None)

    @classmethod
    def _installation_warnings(
        cls,
        study: CableSizingInput,
    ) -> tuple[CableEngineeringWarning, ...]:
        warnings: list[CableEngineeringWarning] = []
        if study.installation.combined_derating_factor < Decimal("0.70"):
            warnings.append(
                CableEngineeringWarning(
                    code=CableWarningCode.HIGH_TOTAL_DERATING,
                    message="Combined installation derating factor is below 0.70",
                    field_name="combined_derating_factor",
                )
            )
        if (
            study.installation.method
            in {
                InstallationMethod.D1_GROUND_DUCT,
                InstallationMethod.D2_DIRECT_BURIED,
            }
            and study.installation.soil_thermal_resistivity_k_m_per_w is None
        ):
            warnings.append(
                CableEngineeringWarning(
                    code=CableWarningCode.SOIL_DATA_REQUIRED,
                    message=(
                        "Project soil thermal resistivity should be confirmed for buried cables"
                    ),
                    field_name="soil_thermal_resistivity_k_m_per_w",
                )
            )
        return tuple(warnings)

    @classmethod
    def _selection_warnings(
        cls,
        study: CableSizingInput,
        ampacity: CableAmpacityResult,
    ) -> tuple[CableEngineeringWarning, ...]:
        warnings: list[CableEngineeringWarning] = []
        if study.cable.parallel_runs > 1:
            warnings.append(
                CableEngineeringWarning(
                    code=CableWarningCode.PARALLEL_CABLE_CURRENT_SHARING,
                    message=(
                        "Parallel runs require equal length, routing, termination, and impedance"
                    ),
                    field_name="parallel_runs",
                )
            )
        if ampacity.utilization_ratio > Decimal("0.90"):
            warnings.append(
                CableEngineeringWarning(
                    code=CableWarningCode.AMPACITY_INADEQUATE,
                    message="Selected cable ampacity utilization exceeds 90 percent",
                    field_name="utilization_ratio",
                )
            )
        return tuple(warnings)

    @staticmethod
    def _governing_criterion(
        ampacity: CableAmpacityResult,
        voltage_drop: CableVoltageDropResult,
        short_circuit: CableShortCircuitResult,
    ) -> str:
        margins = {
            "AMPACITY": Decimal("1") - ampacity.utilization_ratio,
            "VOLTAGE_DROP": (
                voltage_drop.allowable_voltage_drop_percent - voltage_drop.voltage_drop_percent
            )
            / voltage_drop.allowable_voltage_drop_percent,
        }
        if short_circuit.required_area_mm2 is not None:
            margins["SHORT_CIRCUIT_WITHSTAND"] = (
                short_circuit.selected_area_mm2 - short_circuit.required_area_mm2
            ) / short_circuit.selected_area_mm2
        return min(margins, key=margins.__getitem__)

    @staticmethod
    def _deduplicate_warnings(
        warnings: tuple[CableEngineeringWarning, ...],
    ) -> tuple[CableEngineeringWarning, ...]:
        return tuple({warning.code: warning for warning in warnings}.values())

    @classmethod
    def _round(cls, value: Decimal) -> Decimal:
        return value.quantize(cls._FOUR_PLACES, rounding=ROUND_HALF_UP)


__all__ = ["CableSizingEngine"]
