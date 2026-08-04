"""
Immutable domain models for cable sizing and ampacity engineering.
KESE-S2-M13
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.sources.common import (
    normalize_optional_text,
    normalize_required_text,
    require_non_negative_decimal,
    require_positive_decimal,
    require_ratio,
    validate_positive_rating_schedule,
)


class ConductorMaterial(StrEnum):
    """Supported cable conductor materials."""

    COPPER = "COPPER"
    ALUMINIUM = "ALUMINIUM"


class InsulationMaterial(StrEnum):
    """Supported cable insulation systems."""

    PVC = "PVC"
    XLPE = "XLPE"
    EPR = "EPR"
    MINERAL = "MINERAL"


class CableConstruction(StrEnum):
    """Cable construction relevant to thermal and sizing calculations."""

    SINGLE_CORE = "SINGLE_CORE"
    MULTICORE = "MULTICORE"


class CircuitSystem(StrEnum):
    """Supported AC and DC circuit systems."""

    DC_TWO_WIRE = "DC_TWO_WIRE"
    SINGLE_PHASE_AC = "SINGLE_PHASE_AC"
    THREE_PHASE_THREE_WIRE = "THREE_PHASE_THREE_WIRE"
    THREE_PHASE_FOUR_WIRE = "THREE_PHASE_FOUR_WIRE"


class InstallationMethod(StrEnum):
    """IEC 60364 reference installation methods and engineered arrangements."""

    A1_INSULATED_WALL_CONDUIT = "A1_INSULATED_WALL_CONDUIT"
    A2_INSULATED_WALL_MULTICORE = "A2_INSULATED_WALL_MULTICORE"
    B1_WALL_CONDUIT_SINGLE_CORE = "B1_WALL_CONDUIT_SINGLE_CORE"
    B2_WALL_CONDUIT_MULTICORE = "B2_WALL_CONDUIT_MULTICORE"
    C_CLIPPED_DIRECT = "C_CLIPPED_DIRECT"
    D1_GROUND_DUCT = "D1_GROUND_DUCT"
    D2_DIRECT_BURIED = "D2_DIRECT_BURIED"
    E_FREE_AIR_MULTICORE = "E_FREE_AIR_MULTICORE"
    F_FREE_AIR_TOUCHING_SINGLE_CORE = "F_FREE_AIR_TOUCHING_SINGLE_CORE"
    G_FREE_AIR_SPACED_SINGLE_CORE = "G_FREE_AIR_SPACED_SINGLE_CORE"
    CABLE_TRAY = "CABLE_TRAY"
    CABLE_LADDER = "CABLE_LADDER"
    ENGINEERED_IEC_60287 = "ENGINEERED_IEC_60287"


class ConductorArrangement(StrEnum):
    """Physical arrangement of current-carrying conductors."""

    MULTICORE = "MULTICORE"
    FLAT_TOUCHING = "FLAT_TOUCHING"
    FLAT_SPACED = "FLAT_SPACED"
    TREFOIL_TOUCHING = "TREFOIL_TOUCHING"
    TREFOIL_SPACED = "TREFOIL_SPACED"


class ProtectiveConductorType(StrEnum):
    """Protective conductor implementation."""

    INTEGRAL_CORE = "INTEGRAL_CORE"
    SEPARATE_INSULATED = "SEPARATE_INSULATED"
    SEPARATE_BARE = "SEPARATE_BARE"
    METALLIC_SCREEN = "METALLIC_SCREEN"
    METALLIC_ARMOUR = "METALLIC_ARMOUR"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class CableCircuitInput:
    """Electrical duty imposed on a cable circuit."""

    design_current_a: Decimal
    nominal_voltage_v: Decimal
    route_length_m: Decimal
    system: CircuitSystem

    power_factor: Decimal = Decimal("1")
    allowable_voltage_drop_percent: Decimal = Decimal("5")
    fault_current_ka: Decimal | None = None
    fault_duration_s: Decimal | None = None
    harmonic_neutral_factor: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        """Validate circuit duty inputs."""

        require_positive_decimal("design_current_a", self.design_current_a)
        require_positive_decimal("nominal_voltage_v", self.nominal_voltage_v)
        require_non_negative_decimal("route_length_m", self.route_length_m)
        require_ratio("power_factor", self.power_factor)
        require_positive_decimal(
            "allowable_voltage_drop_percent",
            self.allowable_voltage_drop_percent,
        )
        require_positive_decimal("harmonic_neutral_factor", self.harmonic_neutral_factor)

        if not isinstance(self.system, CircuitSystem):
            raise TypeError("system must be a CircuitSystem value")

        if self.allowable_voltage_drop_percent > Decimal("100"):
            raise ValueError("allowable_voltage_drop_percent must not exceed 100")

        if (self.fault_current_ka is None) != (self.fault_duration_s is None):
            raise ValueError("fault_current_ka and fault_duration_s must be provided together")

        if self.fault_current_ka is not None:
            require_positive_decimal("fault_current_ka", self.fault_current_ka)
            assert self.fault_duration_s is not None
            require_positive_decimal("fault_duration_s", self.fault_duration_s)


@dataclass(frozen=True, slots=True)
class CableConstructionInput:
    """Cable material, insulation, core, and conductor configuration."""

    conductor_material: ConductorMaterial
    insulation_material: InsulationMaterial
    construction: CableConstruction
    arrangement: ConductorArrangement

    number_of_loaded_conductors: int
    parallel_runs: int = 1
    neutral_required: bool = True
    reduced_neutral_permitted: bool = False
    protective_conductor_type: ProtectiveConductorType = ProtectiveConductorType.INTEGRAL_CORE
    armoured: bool = False

    def __post_init__(self) -> None:
        """Validate cable construction choices."""

        enum_fields: tuple[tuple[str, object, type[StrEnum]], ...] = (
            ("conductor_material", self.conductor_material, ConductorMaterial),
            ("insulation_material", self.insulation_material, InsulationMaterial),
            ("construction", self.construction, CableConstruction),
            ("arrangement", self.arrangement, ConductorArrangement),
            (
                "protective_conductor_type",
                self.protective_conductor_type,
                ProtectiveConductorType,
            ),
        )
        for field_name, value, enum_type in enum_fields:
            if not isinstance(value, enum_type):
                raise TypeError(f"{field_name} must be a {enum_type.__name__} value")

        if not isinstance(self.number_of_loaded_conductors, int) or isinstance(
            self.number_of_loaded_conductors,
            bool,
        ):
            raise TypeError("number_of_loaded_conductors must be an integer")
        if self.number_of_loaded_conductors < 1:
            raise ValueError("number_of_loaded_conductors must be at least 1")

        if not isinstance(self.parallel_runs, int) or isinstance(self.parallel_runs, bool):
            raise TypeError("parallel_runs must be an integer")
        if self.parallel_runs < 1:
            raise ValueError("parallel_runs must be at least 1")

        if self.number_of_loaded_conductors > 4:
            raise ValueError("number_of_loaded_conductors must not exceed 4")

        if self.construction is CableConstruction.MULTICORE:
            if self.arrangement is not ConductorArrangement.MULTICORE:
                raise ValueError("multicore construction requires MULTICORE arrangement")
        elif self.arrangement is ConductorArrangement.MULTICORE:
            raise ValueError("single-core construction requires a single-core arrangement")

        if self.reduced_neutral_permitted and not self.neutral_required:
            raise ValueError("reduced_neutral_permitted requires neutral_required")


@dataclass(frozen=True, slots=True)
class CableInstallationInput:
    """Installation environment and independently established derating factors."""

    method: InstallationMethod
    ambient_temperature_c: Decimal

    ambient_derating_factor: Decimal = Decimal("1")
    grouping_derating_factor: Decimal = Decimal("1")
    thermal_insulation_factor: Decimal = Decimal("1")
    depth_derating_factor: Decimal = Decimal("1")
    soil_thermal_resistivity_factor: Decimal = Decimal("1")

    grouped_circuits: int = 1
    burial_depth_m: Decimal | None = None
    soil_thermal_resistivity_k_m_per_w: Decimal | None = None
    conductor_spacing_mm: Decimal | None = None

    def __post_init__(self) -> None:
        """Validate installation and derating inputs."""

        if not isinstance(self.method, InstallationMethod):
            raise TypeError("method must be an InstallationMethod value")

        require_non_negative_decimal("ambient_temperature_c", self.ambient_temperature_c)

        for field_name in (
            "ambient_derating_factor",
            "grouping_derating_factor",
            "thermal_insulation_factor",
            "depth_derating_factor",
            "soil_thermal_resistivity_factor",
        ):
            require_ratio(field_name, getattr(self, field_name))

        if not isinstance(self.grouped_circuits, int) or isinstance(self.grouped_circuits, bool):
            raise TypeError("grouped_circuits must be an integer")
        if self.grouped_circuits < 1:
            raise ValueError("grouped_circuits must be at least 1")

        for field_name in (
            "burial_depth_m",
            "soil_thermal_resistivity_k_m_per_w",
            "conductor_spacing_mm",
        ):
            value = getattr(self, field_name)
            if value is not None:
                require_positive_decimal(field_name, value)

        buried_methods = {
            InstallationMethod.D1_GROUND_DUCT,
            InstallationMethod.D2_DIRECT_BURIED,
        }
        has_soil_data = (
            self.burial_depth_m is not None or self.soil_thermal_resistivity_k_m_per_w is not None
        )
        if has_soil_data and self.method not in buried_methods:
            raise ValueError("burial and soil data require a D1 or D2 installation method")

    @property
    def combined_derating_factor(self) -> Decimal:
        """Return the product of all independent derating factors."""

        return (
            self.ambient_derating_factor
            * self.grouping_derating_factor
            * self.thermal_insulation_factor
            * self.depth_derating_factor
            * self.soil_thermal_resistivity_factor
        )


@dataclass(frozen=True, slots=True)
class CableSizeSchedule:
    """Approved standard conductor cross-sectional areas."""

    phase_sizes_mm2: tuple[Decimal, ...]
    neutral_sizes_mm2: tuple[Decimal, ...] | None = None
    protective_sizes_mm2: tuple[Decimal, ...] | None = None

    def __post_init__(self) -> None:
        """Validate standard cable size schedules."""

        validate_positive_rating_schedule(
            field_name="phase_sizes_mm2",
            ratings=self.phase_sizes_mm2,
            empty_message="phase size schedule must not be empty",
            duplicate_message="phase sizes must be unique",
            order_message="phase sizes must be in ascending order",
        )
        for field_name in ("neutral_sizes_mm2", "protective_sizes_mm2"):
            ratings = getattr(self, field_name)
            if ratings is not None:
                validate_positive_rating_schedule(
                    field_name=field_name,
                    ratings=ratings,
                    empty_message=f"{field_name} must not be empty when provided",
                    duplicate_message=f"{field_name} values must be unique",
                    order_message=f"{field_name} values must be in ascending order",
                )


@dataclass(frozen=True, slots=True)
class CableSizingInput:
    """Complete immutable input for an IEC cable sizing study."""

    code: str
    name: str
    circuit: CableCircuitInput
    cable: CableConstructionInput
    installation: CableInstallationInput
    size_schedule: CableSizeSchedule

    standard_reference: str = "IEC 60364-5-52"
    ampacity_reference: str = "IEC 60287"
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the cable sizing study."""

        object.__setattr__(self, "code", normalize_required_text("code", self.code))
        object.__setattr__(self, "name", normalize_required_text("name", self.name))
        object.__setattr__(
            self,
            "standard_reference",
            normalize_required_text("standard_reference", self.standard_reference),
        )
        object.__setattr__(
            self,
            "ampacity_reference",
            normalize_required_text("ampacity_reference", self.ampacity_reference),
        )
        object.__setattr__(self, "notes", normalize_optional_text("notes", self.notes))

        record_fields = (
            ("circuit", self.circuit, CableCircuitInput),
            ("cable", self.cable, CableConstructionInput),
            ("installation", self.installation, CableInstallationInput),
            ("size_schedule", self.size_schedule, CableSizeSchedule),
        )
        for field_name, value, record_type in record_fields:
            if not isinstance(value, record_type):
                raise TypeError(f"{field_name} must be a {record_type.__name__} record")

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


__all__ = [
    "CableCircuitInput",
    "CableConstruction",
    "CableConstructionInput",
    "CableInstallationInput",
    "CableSizeSchedule",
    "CableSizingInput",
    "CircuitSystem",
    "ConductorArrangement",
    "ConductorMaterial",
    "InstallationMethod",
    "InsulationMaterial",
    "ProtectiveConductorType",
]
