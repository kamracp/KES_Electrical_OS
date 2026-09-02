"""
Immutable short-circuit and earth-fault engineering domain models.
KESE-S2-M15
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
)


class FaultType(StrEnum):
    """Fault configurations supported by the IEC 60909 study contract."""

    THREE_PHASE = "THREE_PHASE"
    TWO_PHASE = "TWO_PHASE"
    TWO_PHASE_TO_EARTH = "TWO_PHASE_TO_EARTH"
    SINGLE_PHASE_TO_EARTH = "SINGLE_PHASE_TO_EARTH"


class ShortCircuitCase(StrEnum):
    """Maximum or minimum prospective short-circuit calculation case."""

    MAXIMUM = "MAXIMUM"
    MINIMUM = "MINIMUM"


class FaultSourceType(StrEnum):
    """Source categories contributing to a short-circuit study."""

    UTILITY_GRID = "UTILITY_GRID"
    SYNCHRONOUS_GENERATOR = "SYNCHRONOUS_GENERATOR"
    ASYNCHRONOUS_MOTOR = "ASYNCHRONOUS_MOTOR"
    INVERTER_BASED_RESOURCE = "INVERTER_BASED_RESOURCE"
    EQUIVALENT_SOURCE = "EQUIVALENT_SOURCE"


class SourceRepresentation(StrEnum):
    """Electrical representation used for a fault-current source."""

    VOLTAGE_BEHIND_IMPEDANCE = "VOLTAGE_BEHIND_IMPEDANCE"
    CURRENT_INJECTION = "CURRENT_INJECTION"


class FaultBranchType(StrEnum):
    """Network branch categories relevant to sequence impedance."""

    CABLE = "CABLE"
    OVERHEAD_LINE = "OVERHEAD_LINE"
    TRANSFORMER = "TRANSFORMER"
    BUSBAR = "BUSBAR"
    BUSDUCT = "BUSDUCT"
    REACTOR = "REACTOR"
    EQUIVALENT = "EQUIVALENT"


class NeutralEarthingMode(StrEnum):
    """Neutral treatment at an electrical fault bus."""

    SOLIDLY_EARTHED = "SOLIDLY_EARTHED"
    RESISTANCE_EARTHED = "RESISTANCE_EARTHED"
    REACTANCE_EARTHED = "REACTANCE_EARTHED"
    RESONANT_EARTHED = "RESONANT_EARTHED"
    ISOLATED = "ISOLATED"


_UNBALANCED_FAULT_TYPES = {
    FaultType.TWO_PHASE,
    FaultType.TWO_PHASE_TO_EARTH,
    FaultType.SINGLE_PHASE_TO_EARTH,
}


def _require_boolean(field_name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean")


def _require_positive_integer(field_name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer")
    if value < 1:
        raise ValueError(f"{field_name} must be at least 1")


@dataclass(frozen=True, slots=True)
class SequenceImpedanceInput:
    """Exact resistance and reactance for one symmetrical sequence."""

    resistance_ohm: Decimal
    reactance_ohm: Decimal

    def __post_init__(self) -> None:
        """Validate a finite non-zero inductive impedance."""

        require_non_negative_decimal("resistance_ohm", self.resistance_ohm)
        require_non_negative_decimal("reactance_ohm", self.reactance_ohm)
        if self.resistance_ohm == self.reactance_ohm == Decimal("0"):
            raise ValueError("sequence impedance must not be zero")


@dataclass(frozen=True, slots=True)
class FaultBusInput:
    """Fault-study bus with voltage factors and neutral treatment."""

    code: str
    name: str
    nominal_voltage_v: Decimal
    voltage_factor_max: Decimal
    voltage_factor_min: Decimal
    neutral_earthing_mode: NeutralEarthingMode

    neutral_resistance_ohm: Decimal = Decimal("0")
    neutral_reactance_ohm: Decimal = Decimal("0")
    sld_node_code: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize bus inputs."""

        object.__setattr__(self, "code", normalize_required_text("code", self.code))
        object.__setattr__(self, "name", normalize_required_text("name", self.name))
        object.__setattr__(
            self,
            "sld_node_code",
            normalize_optional_text("sld_node_code", self.sld_node_code),
        )
        object.__setattr__(
            self,
            "notes",
            normalize_optional_text("notes", self.notes),
        )

        require_positive_decimal("nominal_voltage_v", self.nominal_voltage_v)
        require_positive_decimal("voltage_factor_max", self.voltage_factor_max)
        require_positive_decimal("voltage_factor_min", self.voltage_factor_min)
        if self.voltage_factor_min > self.voltage_factor_max:
            raise ValueError("voltage_factor_min must not exceed voltage_factor_max")

        if not isinstance(self.neutral_earthing_mode, NeutralEarthingMode):
            raise TypeError("neutral_earthing_mode must be a NeutralEarthingMode value")

        require_non_negative_decimal(
            "neutral_resistance_ohm",
            self.neutral_resistance_ohm,
        )
        require_non_negative_decimal(
            "neutral_reactance_ohm",
            self.neutral_reactance_ohm,
        )
        has_resistance = self.neutral_resistance_ohm > Decimal("0")
        has_reactance = self.neutral_reactance_ohm > Decimal("0")

        if self.neutral_earthing_mode is NeutralEarthingMode.SOLIDLY_EARTHED:
            if has_resistance or has_reactance:
                raise ValueError("SOLIDLY_EARTHED bus requires zero neutral impedance")
        elif self.neutral_earthing_mode is NeutralEarthingMode.RESISTANCE_EARTHED:
            if not has_resistance:
                raise ValueError("RESISTANCE_EARTHED bus requires neutral resistance")
        elif self.neutral_earthing_mode in {
            NeutralEarthingMode.REACTANCE_EARTHED,
            NeutralEarthingMode.RESONANT_EARTHED,
        }:
            if not has_reactance:
                raise ValueError(
                    f"{self.neutral_earthing_mode.value} bus requires neutral reactance"
                )
        elif has_resistance or has_reactance:
            raise ValueError("ISOLATED bus cannot define a neutral earthing impedance")


@dataclass(frozen=True, slots=True)
class FaultSourceInput:
    """Source contribution connected to one fault-study bus."""

    code: str
    name: str
    bus_code: str
    source_type: FaultSourceType
    representation: SourceRepresentation

    positive_sequence_impedance: SequenceImpedanceInput | None
    negative_sequence_impedance: SequenceImpedanceInput | None
    zero_sequence_impedance: SequenceImpedanceInput | None
    current_contribution_ka: Decimal | None

    in_service: bool = True
    contribution_factor: Decimal = Decimal("1")
    equipment_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize source contribution data."""

        for field_name in ("code", "name", "bus_code"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(field_name, getattr(self, field_name)),
            )
        for field_name in ("equipment_reference", "notes"):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(field_name, getattr(self, field_name)),
            )

        if not isinstance(self.source_type, FaultSourceType):
            raise TypeError("source_type must be a FaultSourceType value")
        if not isinstance(self.representation, SourceRepresentation):
            raise TypeError("representation must be a SourceRepresentation value")
        _require_boolean("in_service", self.in_service)
        require_ratio("contribution_factor", self.contribution_factor)

        impedance_fields = (
            ("positive_sequence_impedance", self.positive_sequence_impedance),
            ("negative_sequence_impedance", self.negative_sequence_impedance),
            ("zero_sequence_impedance", self.zero_sequence_impedance),
        )
        for field_name, value in impedance_fields:
            if value is not None and not isinstance(value, SequenceImpedanceInput):
                raise TypeError(f"{field_name} must be a SequenceImpedanceInput or None")

        if self.representation is SourceRepresentation.VOLTAGE_BEHIND_IMPEDANCE:
            if self.positive_sequence_impedance is None:
                raise ValueError(
                    "VOLTAGE_BEHIND_IMPEDANCE source requires positive-sequence impedance"
                )
            if self.current_contribution_ka is not None:
                raise ValueError(
                    "VOLTAGE_BEHIND_IMPEDANCE source cannot define current_contribution_ka"
                )
        else:
            if any(value is not None for _, value in impedance_fields):
                raise ValueError("CURRENT_INJECTION source cannot define sequence impedances")
            if self.current_contribution_ka is None:
                raise ValueError("CURRENT_INJECTION source requires current_contribution_ka")

        if self.current_contribution_ka is not None:
            require_positive_decimal(
                "current_contribution_ka",
                self.current_contribution_ka,
            )


@dataclass(frozen=True, slots=True)
class FaultBranchInput:
    """Per-circuit sequence impedance between two fault-study buses."""

    code: str
    name: str
    from_bus_code: str
    to_bus_code: str
    branch_type: FaultBranchType

    positive_sequence_impedance: SequenceImpedanceInput
    negative_sequence_impedance: SequenceImpedanceInput | None
    zero_sequence_impedance: SequenceImpedanceInput | None

    parallel_circuits: int = 1
    in_service: bool = True
    equipment_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize branch impedance data."""

        for field_name in ("code", "name", "from_bus_code", "to_bus_code"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(field_name, getattr(self, field_name)),
            )
        for field_name in ("equipment_reference", "notes"):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(field_name, getattr(self, field_name)),
            )

        if not isinstance(self.branch_type, FaultBranchType):
            raise TypeError("branch_type must be a FaultBranchType value")
        if self.from_bus_code == self.to_bus_code:
            raise ValueError("a fault branch cannot connect a bus to itself")
        if not isinstance(self.positive_sequence_impedance, SequenceImpedanceInput):
            raise TypeError("positive_sequence_impedance must be a SequenceImpedanceInput")
        for field_name in (
            "negative_sequence_impedance",
            "zero_sequence_impedance",
        ):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, SequenceImpedanceInput):
                raise TypeError(f"{field_name} must be a SequenceImpedanceInput or None")

        _require_positive_integer("parallel_circuits", self.parallel_circuits)
        _require_boolean("in_service", self.in_service)


@dataclass(frozen=True, slots=True)
class FaultLocationInput:
    """Fault type, location, path impedance, and optional clearing duty."""

    bus_code: str
    fault_type: FaultType
    fault_resistance_ohm: Decimal = Decimal("0")
    fault_reactance_ohm: Decimal = Decimal("0")
    clearing_time_s: Decimal | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize fault-location inputs."""

        object.__setattr__(
            self,
            "bus_code",
            normalize_required_text("bus_code", self.bus_code),
        )
        object.__setattr__(
            self,
            "description",
            normalize_optional_text("description", self.description),
        )
        if not isinstance(self.fault_type, FaultType):
            raise TypeError("fault_type must be a FaultType value")

        require_non_negative_decimal(
            "fault_resistance_ohm",
            self.fault_resistance_ohm,
        )
        require_non_negative_decimal(
            "fault_reactance_ohm",
            self.fault_reactance_ohm,
        )
        if self.clearing_time_s is not None:
            require_positive_decimal("clearing_time_s", self.clearing_time_s)


@dataclass(frozen=True, slots=True)
class ShortCircuitStudyInput:
    """Complete immutable IEC 60909 short-circuit study input."""

    code: str
    name: str
    calculation_case: ShortCircuitCase
    fault: FaultLocationInput
    buses: tuple[FaultBusInput, ...]
    sources: tuple[FaultSourceInput, ...]
    branches: tuple[FaultBranchInput, ...] = ()

    frequency_hz: Decimal = Decimal("50")
    operating_state_code: str | None = None
    standard_reference: str = "IEC 60909-0:2026"
    earth_current_reference: str = "IEC 60909-3:2009"
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate the study topology, references, and sequence-data contract."""

        object.__setattr__(self, "code", normalize_required_text("code", self.code))
        object.__setattr__(self, "name", normalize_required_text("name", self.name))
        for field_name in ("operating_state_code", "notes"):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(field_name, getattr(self, field_name)),
            )
        for field_name in ("standard_reference", "earth_current_reference"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(field_name, getattr(self, field_name)),
            )

        if not isinstance(self.calculation_case, ShortCircuitCase):
            raise TypeError("calculation_case must be a ShortCircuitCase value")
        if not isinstance(self.fault, FaultLocationInput):
            raise TypeError("fault must be a FaultLocationInput record")

        collections: tuple[tuple[str, tuple[object, ...], type[object]], ...] = (
            ("buses", self.buses, FaultBusInput),
            ("sources", self.sources, FaultSourceInput),
            ("branches", self.branches, FaultBranchInput),
        )
        for field_name, records, record_type in collections:
            if not isinstance(records, tuple):
                raise TypeError(f"{field_name} must be a tuple")
            if not all(isinstance(record, record_type) for record in records):
                raise TypeError(f"{field_name} must contain only {record_type.__name__} records")

        if not self.buses:
            raise ValueError("a short-circuit study requires at least one bus")
        if not self.sources:
            raise ValueError("a short-circuit study requires at least one source")

        require_positive_decimal("frequency_hz", self.frequency_hz)
        if self.frequency_hz not in {Decimal("50"), Decimal("60")}:
            raise ValueError("frequency_hz must be 50 or 60 for an IEC 60909 study")

        bus_by_code = {bus.code: bus for bus in self.buses}
        source_codes = {source.code for source in self.sources}
        branch_codes = {branch.code for branch in self.branches}
        if len(bus_by_code) != len(self.buses):
            raise ValueError("fault bus codes must be unique")
        if len(source_codes) != len(self.sources):
            raise ValueError("fault source codes must be unique")
        if len(branch_codes) != len(self.branches):
            raise ValueError("fault branch codes must be unique")

        if self.fault.bus_code not in bus_by_code:
            raise ValueError("fault location references an unknown bus")

        for source in self.sources:
            if source.bus_code not in bus_by_code:
                raise ValueError(f"source {source.code} references an unknown bus")
        if not any(source.in_service for source in self.sources):
            raise ValueError("a short-circuit study requires an in-service source")

        for branch in self.branches:
            if branch.from_bus_code not in bus_by_code:
                raise ValueError(f"branch {branch.code} references an unknown from_bus_code")
            if branch.to_bus_code not in bus_by_code:
                raise ValueError(f"branch {branch.code} references an unknown to_bus_code")

        if self.fault.fault_type in _UNBALANCED_FAULT_TYPES:
            sources_missing_negative_sequence = tuple(
                source.code
                for source in self.sources
                if source.in_service
                and source.representation is SourceRepresentation.VOLTAGE_BEHIND_IMPEDANCE
                and source.negative_sequence_impedance is None
            )
            if sources_missing_negative_sequence:
                raise ValueError(
                    "unbalanced fault study requires explicit source negative-sequence data"
                )

            branches_missing_negative_sequence = tuple(
                branch.code
                for branch in self.branches
                if branch.in_service and branch.negative_sequence_impedance is None
            )
            if branches_missing_negative_sequence:
                raise ValueError(
                    "unbalanced fault study requires explicit branch negative-sequence data"
                )


__all__ = [
    "FaultBranchInput",
    "FaultBranchType",
    "FaultBusInput",
    "FaultLocationInput",
    "FaultSourceInput",
    "FaultSourceType",
    "FaultType",
    "NeutralEarthingMode",
    "SequenceImpedanceInput",
    "ShortCircuitCase",
    "ShortCircuitStudyInput",
    "SourceRepresentation",
]
