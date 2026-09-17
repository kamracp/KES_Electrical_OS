"""
Pydantic schemas for cable sizing and voltage drop engineering calculations.
KESE-S2-M13
"""

from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    model_validator,
)

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
    CableAmpacityResult,
    CableCheckStatus,
    CableConductorSizingResult,
    CableEngineeringWarning,
    CableReferenceSource,
    CableShortCircuitResult,
    CableSizingResult,
    CableSizingStatus,
    CableVoltageDropResult,
    CableWarningCode,
)
from app.domain.electrical.jurisdiction.jurisdiction_models import (
    JurisdictionProfile,
    ReferenceVerificationStatus,
)


def _reject_float(value: object) -> object:
    """Reject binary floating-point engineering inputs."""

    if isinstance(value, float):
        raise ValueError(
            "engineering decimal values must be provided as strings, integers, or Decimal values"
        )

    return value


type PositiveExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
    Field(
        gt=Decimal("0"),
        max_digits=38,
        decimal_places=18,
    ),
]

type NonNegativeExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
    Field(
        ge=Decimal("0"),
        max_digits=38,
        decimal_places=18,
    ),
]

type RatioExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
    Field(
        gt=Decimal("0"),
        le=Decimal("1"),
        max_digits=38,
        decimal_places=18,
    ),
]

type PercentExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
    Field(
        gt=Decimal("0"),
        le=Decimal("100"),
        max_digits=38,
        decimal_places=18,
    ),
]


class CableCircuitInputSchema(BaseModel):
    """Schema for electrical circuit duty imposed on a cable."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    design_current_a: PositiveExactDecimal
    nominal_voltage_v: PositiveExactDecimal
    route_length_m: NonNegativeExactDecimal
    system: CircuitSystem
    power_factor: RatioExactDecimal = Field(default=Decimal("1"))
    allowable_voltage_drop_percent: PercentExactDecimal = Field(default=Decimal("5"))
    fault_current_ka: PositiveExactDecimal | None = None
    fault_duration_s: PositiveExactDecimal | None = None
    harmonic_neutral_factor: PositiveExactDecimal = Field(default=Decimal("1"))

    @model_validator(mode="after")
    def validate_fault_inputs(self) -> Self:
        """Ensure fault current and duration are provided together."""

        if (self.fault_current_ka is None) != (self.fault_duration_s is None):
            raise ValueError("fault_current_ka and fault_duration_s must be provided together")

        return self

    def to_domain(self) -> CableCircuitInput:
        """Convert to domain dataclass."""

        return CableCircuitInput(
            design_current_a=self.design_current_a,
            nominal_voltage_v=self.nominal_voltage_v,
            route_length_m=self.route_length_m,
            system=self.system,
            power_factor=self.power_factor,
            allowable_voltage_drop_percent=self.allowable_voltage_drop_percent,
            fault_current_ka=self.fault_current_ka,
            fault_duration_s=self.fault_duration_s,
            harmonic_neutral_factor=self.harmonic_neutral_factor,
        )


class CableConstructionInputSchema(BaseModel):
    """Schema for cable construction, material and conductor arrangement."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    conductor_material: ConductorMaterial
    insulation_material: InsulationMaterial
    construction: CableConstruction
    arrangement: ConductorArrangement
    number_of_loaded_conductors: StrictInt = Field(ge=1, le=4)
    parallel_runs: StrictInt = Field(default=1, ge=1)
    neutral_required: StrictBool = True
    reduced_neutral_permitted: StrictBool = False
    protective_conductor_type: ProtectiveConductorType = ProtectiveConductorType.INTEGRAL_CORE
    armoured: StrictBool = False

    @model_validator(mode="after")
    def validate_construction_arrangement(self) -> Self:
        """Validate alignment between construction and arrangement."""

        if self.construction is CableConstruction.MULTICORE:
            if self.arrangement is not ConductorArrangement.MULTICORE:
                raise ValueError("multicore construction requires MULTICORE arrangement")
        elif self.arrangement is ConductorArrangement.MULTICORE:
            raise ValueError("single-core construction requires a single-core arrangement")

        if self.reduced_neutral_permitted and not self.neutral_required:
            raise ValueError("reduced_neutral_permitted requires neutral_required")

        return self

    def to_domain(self) -> CableConstructionInput:
        """Convert to domain dataclass."""

        return CableConstructionInput(
            conductor_material=self.conductor_material,
            insulation_material=self.insulation_material,
            construction=self.construction,
            arrangement=self.arrangement,
            number_of_loaded_conductors=self.number_of_loaded_conductors,
            parallel_runs=self.parallel_runs,
            neutral_required=self.neutral_required,
            reduced_neutral_permitted=self.reduced_neutral_permitted,
            protective_conductor_type=self.protective_conductor_type,
            armoured=self.armoured,
        )


class CableInstallationInputSchema(BaseModel):
    """Schema for installation environment and derating factors."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    method: InstallationMethod
    ambient_temperature_c: NonNegativeExactDecimal
    ambient_derating_factor: RatioExactDecimal = Field(default=Decimal("1"))
    grouping_derating_factor: RatioExactDecimal = Field(default=Decimal("1"))
    thermal_insulation_factor: RatioExactDecimal = Field(default=Decimal("1"))
    depth_derating_factor: RatioExactDecimal = Field(default=Decimal("1"))
    soil_thermal_resistivity_factor: RatioExactDecimal = Field(default=Decimal("1"))
    grouped_circuits: StrictInt = Field(default=1, ge=1)
    burial_depth_m: PositiveExactDecimal | None = None
    soil_thermal_resistivity_k_m_per_w: PositiveExactDecimal | None = None
    conductor_spacing_mm: PositiveExactDecimal | None = None

    @model_validator(mode="after")
    def validate_buried_data(self) -> Self:
        """Verify soil inputs are provided only for buried methods."""

        buried_methods = {
            InstallationMethod.D1_GROUND_DUCT,
            InstallationMethod.D2_DIRECT_BURIED,
        }
        has_soil_data = (
            self.burial_depth_m is not None or self.soil_thermal_resistivity_k_m_per_w is not None
        )
        if has_soil_data and self.method not in buried_methods:
            raise ValueError("burial and soil data require a D1 or D2 installation method")

        return self

    def to_domain(self) -> CableInstallationInput:
        """Convert to domain dataclass."""

        return CableInstallationInput(
            method=self.method,
            ambient_temperature_c=self.ambient_temperature_c,
            ambient_derating_factor=self.ambient_derating_factor,
            grouping_derating_factor=self.grouping_derating_factor,
            thermal_insulation_factor=self.thermal_insulation_factor,
            depth_derating_factor=self.depth_derating_factor,
            soil_thermal_resistivity_factor=self.soil_thermal_resistivity_factor,
            grouped_circuits=self.grouped_circuits,
            burial_depth_m=self.burial_depth_m,
            soil_thermal_resistivity_k_m_per_w=self.soil_thermal_resistivity_k_m_per_w,
            conductor_spacing_mm=self.conductor_spacing_mm,
        )


class CableSizeScheduleSchema(BaseModel):
    """Schema for standard conductor size schedules."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    phase_sizes_mm2: list[PositiveExactDecimal] = Field(min_length=1)
    neutral_sizes_mm2: list[PositiveExactDecimal] | None = None
    protective_sizes_mm2: list[PositiveExactDecimal] | None = None

    @model_validator(mode="after")
    def validate_schedules(self) -> Self:
        """Verify schedules are unique and strictly ascending."""

        def check_ascending(ratings: list[Decimal], field_name: str) -> None:
            if len(ratings) != len(set(ratings)):
                raise ValueError(f"{field_name} must be unique")
            if ratings != sorted(ratings):
                raise ValueError(f"{field_name} must be in ascending order")

        check_ascending(self.phase_sizes_mm2, "phase_sizes_mm2")
        if self.neutral_sizes_mm2 is not None:
            check_ascending(self.neutral_sizes_mm2, "neutral_sizes_mm2")
        if self.protective_sizes_mm2 is not None:
            check_ascending(self.protective_sizes_mm2, "protective_sizes_mm2")

        return self

    def to_domain(self) -> CableSizeSchedule:
        """Convert to domain dataclass."""

        return CableSizeSchedule(
            phase_sizes_mm2=tuple(self.phase_sizes_mm2),
            neutral_sizes_mm2=(
                tuple(self.neutral_sizes_mm2) if self.neutral_sizes_mm2 is not None else None
            ),
            protective_sizes_mm2=(
                tuple(self.protective_sizes_mm2) if self.protective_sizes_mm2 is not None else None
            ),
        )


class CableSizingRequest(BaseModel):
    """Schema for cable sizing calculation request."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    circuit: CableCircuitInputSchema
    cable: CableConstructionInputSchema
    installation: CableInstallationInputSchema
    size_schedule: CableSizeScheduleSchema
    # Governing references default to the jurisdiction profile; supplying both is a
    # project override reported as a deviation on the result.
    standard_reference: str | None = Field(default=None, min_length=1, max_length=80)
    ampacity_reference: str | None = Field(default=None, min_length=1, max_length=80)
    jurisdiction_profile: JurisdictionProfile = JurisdictionProfile.IN
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _references_overridden_together(self) -> Self:
        if (self.standard_reference is None) != (self.ampacity_reference is None):
            raise ValueError("standard_reference and ampacity_reference must be provided together")
        return self

    @model_validator(mode="after")
    def validate_system_neutral(self) -> Self:
        """Cross-validate system and neutral requirements."""

        if (
            self.circuit.system is CircuitSystem.THREE_PHASE_THREE_WIRE
            and self.cable.neutral_required
        ):
            raise ValueError("THREE_PHASE_THREE_WIRE circuit cannot require a neutral conductor")

        if (
            self.circuit.system is CircuitSystem.THREE_PHASE_FOUR_WIRE
            and not self.cable.neutral_required
        ):
            raise ValueError("THREE_PHASE_FOUR_WIRE circuit requires a neutral conductor")

        if self.cable.reduced_neutral_permitted and self.circuit.harmonic_neutral_factor > Decimal(
            "1"
        ):
            raise ValueError(
                "reduced neutral is not permitted when harmonic neutral factor exceeds 1"
            )

        return self

    def to_domain(self) -> CableSizingInput:
        """Convert to domain CableSizingInput dataclass."""

        return CableSizingInput(
            code=self.code,
            name=self.name,
            circuit=self.circuit.to_domain(),
            cable=self.cable.to_domain(),
            installation=self.installation.to_domain(),
            size_schedule=self.size_schedule.to_domain(),
            standard_reference=self.standard_reference,
            ampacity_reference=self.ampacity_reference,
            jurisdiction_profile=self.jurisdiction_profile,
            notes=self.notes,
        )


class CableAmpacityResultSchema(BaseModel):
    """Schema for thermal current-carrying ampacity outcome."""

    model_config = ConfigDict(extra="forbid")

    tabulated_ampacity_a_per_run: Decimal
    combined_derating_factor: Decimal
    derated_ampacity_a_per_run: Decimal
    parallel_runs: int
    total_installed_ampacity_a: Decimal
    design_current_a: Decimal
    required_tabulated_ampacity_a_per_run: Decimal
    utilization_ratio: Decimal
    status: CableCheckStatus

    @classmethod
    def from_domain(cls, result: CableAmpacityResult) -> Self:
        return cls(
            tabulated_ampacity_a_per_run=result.tabulated_ampacity_a_per_run,
            combined_derating_factor=result.combined_derating_factor,
            derated_ampacity_a_per_run=result.derated_ampacity_a_per_run,
            parallel_runs=result.parallel_runs,
            total_installed_ampacity_a=result.total_installed_ampacity_a,
            design_current_a=result.design_current_a,
            required_tabulated_ampacity_a_per_run=result.required_tabulated_ampacity_a_per_run,
            utilization_ratio=result.utilization_ratio,
            status=result.status,
        )


class CableVoltageDropResultSchema(BaseModel):
    """Schema for steady-state voltage drop outcome."""

    model_config = ConfigDict(extra="forbid")

    resistance_ohm_per_km: Decimal
    reactance_ohm_per_km: Decimal
    voltage_drop_v: Decimal
    voltage_drop_percent: Decimal
    allowable_voltage_drop_percent: Decimal
    status: CableCheckStatus

    @classmethod
    def from_domain(cls, result: CableVoltageDropResult) -> Self:
        return cls(
            resistance_ohm_per_km=result.resistance_ohm_per_km,
            reactance_ohm_per_km=result.reactance_ohm_per_km,
            voltage_drop_v=result.voltage_drop_v,
            voltage_drop_percent=result.voltage_drop_percent,
            allowable_voltage_drop_percent=result.allowable_voltage_drop_percent,
            status=result.status,
        )


class CableShortCircuitResultSchema(BaseModel):
    """Schema for adiabatic short-circuit withstand outcome."""

    model_config = ConfigDict(extra="forbid")

    fault_current_ka: Decimal | None = None
    fault_duration_s: Decimal | None = None
    material_constant_k: Decimal | None = None
    required_area_mm2: Decimal | None = None
    selected_area_mm2: Decimal
    withstand_current_ka: Decimal | None = None
    status: CableCheckStatus

    @classmethod
    def from_domain(cls, result: CableShortCircuitResult) -> Self:
        return cls(
            fault_current_ka=result.fault_current_ka,
            fault_duration_s=result.fault_duration_s,
            material_constant_k=result.material_constant_k,
            required_area_mm2=result.required_area_mm2,
            selected_area_mm2=result.selected_area_mm2,
            withstand_current_ka=result.withstand_current_ka,
            status=result.status,
        )


class CableConductorSizingResultSchema(BaseModel):
    """Schema for selected phase, neutral and protective conductor sizes."""

    model_config = ConfigDict(extra="forbid")

    phase_area_mm2: Decimal
    neutral_area_mm2: Decimal | None = None
    protective_area_mm2: Decimal | None = None
    parallel_runs: int
    phase_conductors_per_run: int
    neutral_status: CableCheckStatus
    protective_status: CableCheckStatus

    @classmethod
    def from_domain(cls, result: CableConductorSizingResult) -> Self:
        return cls(
            phase_area_mm2=result.phase_area_mm2,
            neutral_area_mm2=result.neutral_area_mm2,
            protective_area_mm2=result.protective_area_mm2,
            parallel_runs=result.parallel_runs,
            phase_conductors_per_run=result.phase_conductors_per_run,
            neutral_status=result.neutral_status,
            protective_status=result.protective_status,
        )


class CableEngineeringWarningSchema(BaseModel):
    """Schema for cable engineering warnings."""

    model_config = ConfigDict(extra="forbid")

    code: CableWarningCode
    message: str
    field_name: str | None = None

    @classmethod
    def from_domain(cls, warning: CableEngineeringWarning) -> Self:
        return cls(
            code=warning.code,
            message=warning.message,
            field_name=warning.field_name,
        )


class CableSizingResponse(BaseModel):
    """Complete response schema for cable sizing calculation."""

    model_config = ConfigDict(extra="forbid")

    study_code: str
    status: CableSizingStatus
    conductor: CableConductorSizingResultSchema | None = None
    ampacity: CableAmpacityResultSchema | None = None
    voltage_drop: CableVoltageDropResultSchema | None = None
    short_circuit: CableShortCircuitResultSchema | None = None
    warnings: list[CableEngineeringWarningSchema] = Field(default_factory=list)
    standard_reference: str | None = None
    ampacity_reference: str | None = None
    reference_source: CableReferenceSource
    jurisdiction_profile: JurisdictionProfile
    reference_verification_status: ReferenceVerificationStatus
    notes: str | None = None

    @classmethod
    def from_domain(cls, result: CableSizingResult) -> Self:
        """Create response schema from domain CableSizingResult."""

        return cls(
            study_code=result.study_code,
            status=result.status,
            conductor=(
                CableConductorSizingResultSchema.from_domain(result.conductor)
                if result.conductor is not None
                else None
            ),
            ampacity=(
                CableAmpacityResultSchema.from_domain(result.ampacity)
                if result.ampacity is not None
                else None
            ),
            voltage_drop=(
                CableVoltageDropResultSchema.from_domain(result.voltage_drop)
                if result.voltage_drop is not None
                else None
            ),
            short_circuit=(
                CableShortCircuitResultSchema.from_domain(result.short_circuit)
                if result.short_circuit is not None
                else None
            ),
            warnings=[CableEngineeringWarningSchema.from_domain(w) for w in result.warnings],
            standard_reference=result.standard_reference,
            ampacity_reference=result.ampacity_reference,
            reference_source=result.reference_source,
            jurisdiction_profile=result.jurisdiction_profile,
            reference_verification_status=result.reference_verification_status,
            notes=result.notes,
        )


__all__ = [
    "CableAmpacityResultSchema",
    "CableCircuitInputSchema",
    "CableConductorSizingResultSchema",
    "CableConstructionInputSchema",
    "CableEngineeringWarningSchema",
    "CableInstallationInputSchema",
    "CableShortCircuitResultSchema",
    "CableSizeScheduleSchema",
    "CableSizingRequest",
    "CableSizingResponse",
    "CableVoltageDropResultSchema",
]
