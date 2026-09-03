"""
Pydantic schemas for short-circuit and earth-fault engineering.

KESE-S2-M15
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

from app.domain.electrical.fault import (
    EquivalentSequenceImpedanceResult,
    FaultBranchInput,
    FaultBranchType,
    FaultBusInput,
    FaultEngineeringWarning,
    FaultLocationInput,
    FaultResultStatus,
    FaultSequence,
    FaultSourceContributionResult,
    FaultSourceInput,
    FaultSourceType,
    FaultType,
    FaultWarningCode,
    FaultWarningSeverity,
    NeutralEarthingMode,
    SequenceImpedanceInput,
    ShortCircuitCase,
    ShortCircuitStudyInput,
    ShortCircuitStudyResult,
    SourceRepresentation,
)


def _reject_float(value: object) -> object:
    """Reject binary floating-point engineering inputs."""

    if isinstance(value, float):
        raise ValueError(
            "engineering decimal values must be provided as strings, integers, or Decimal values"
        )

    return value


ExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
]


class _RequestBase(BaseModel):
    """Shared fault-study request configuration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class _ResponseBase(BaseModel):
    """Shared fault-study response configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class SequenceImpedanceRequest(_RequestBase):
    """One exact symmetrical-sequence impedance."""

    resistance_ohm: ExactDecimal = Field(
        ge=Decimal("0"),
    )
    reactance_ohm: ExactDecimal = Field(
        ge=Decimal("0"),
    )

    def to_domain(self) -> SequenceImpedanceInput:
        """Convert request to immutable sequence impedance."""

        return SequenceImpedanceInput(
            resistance_ohm=self.resistance_ohm,
            reactance_ohm=self.reactance_ohm,
        )

    @model_validator(mode="after")
    def validate_domain_contract(self) -> Self:
        """Apply domain invariants during request validation."""

        self.to_domain()
        return self


class FaultBusRequest(_RequestBase):
    """Electrical bus participating in a fault study."""

    code: str = Field(
        min_length=1,
        max_length=80,
    )
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    nominal_voltage_v: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    voltage_factor_max: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    voltage_factor_min: ExactDecimal = Field(
        gt=Decimal("0"),
    )

    neutral_earthing_mode: NeutralEarthingMode

    neutral_resistance_ohm: ExactDecimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
    )
    neutral_reactance_ohm: ExactDecimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
    )

    sld_node_code: str | None = Field(
        default=None,
        max_length=80,
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

    def to_domain(self) -> FaultBusInput:
        """Convert request to immutable fault bus."""

        return FaultBusInput(
            code=self.code,
            name=self.name,
            nominal_voltage_v=self.nominal_voltage_v,
            voltage_factor_max=self.voltage_factor_max,
            voltage_factor_min=self.voltage_factor_min,
            neutral_earthing_mode=self.neutral_earthing_mode,
            neutral_resistance_ohm=self.neutral_resistance_ohm,
            neutral_reactance_ohm=self.neutral_reactance_ohm,
            sld_node_code=self.sld_node_code,
            notes=self.notes,
        )

    @model_validator(mode="after")
    def validate_domain_contract(self) -> Self:
        """Apply bus and neutral-earthing invariants."""

        self.to_domain()
        return self


class FaultSourceRequest(_RequestBase):
    """Fault-current source request."""

    code: str = Field(
        min_length=1,
        max_length=80,
    )
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    bus_code: str = Field(
        min_length=1,
        max_length=80,
    )

    source_type: FaultSourceType
    representation: SourceRepresentation

    positive_sequence_impedance: SequenceImpedanceRequest | None = None
    negative_sequence_impedance: SequenceImpedanceRequest | None = None
    zero_sequence_impedance: SequenceImpedanceRequest | None = None

    current_contribution_ka: ExactDecimal | None = Field(
        default=None,
        gt=Decimal("0"),
    )

    in_service: StrictBool = True

    contribution_factor: ExactDecimal = Field(
        default=Decimal("1"),
        gt=Decimal("0"),
        le=Decimal("1"),
    )

    equipment_reference: str | None = Field(
        default=None,
        max_length=120,
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

    def to_domain(self) -> FaultSourceInput:
        """Convert request to immutable fault source."""

        return FaultSourceInput(
            code=self.code,
            name=self.name,
            bus_code=self.bus_code,
            source_type=self.source_type,
            representation=self.representation,
            positive_sequence_impedance=(
                self.positive_sequence_impedance.to_domain()
                if self.positive_sequence_impedance is not None
                else None
            ),
            negative_sequence_impedance=(
                self.negative_sequence_impedance.to_domain()
                if self.negative_sequence_impedance is not None
                else None
            ),
            zero_sequence_impedance=(
                self.zero_sequence_impedance.to_domain()
                if self.zero_sequence_impedance is not None
                else None
            ),
            current_contribution_ka=self.current_contribution_ka,
            in_service=self.in_service,
            contribution_factor=self.contribution_factor,
            equipment_reference=self.equipment_reference,
            notes=self.notes,
        )

    @model_validator(mode="after")
    def validate_domain_contract(self) -> Self:
        """Apply source representation invariants."""

        self.to_domain()
        return self


class FaultBranchRequest(_RequestBase):
    """Network branch participating in the sequence network."""

    code: str = Field(
        min_length=1,
        max_length=80,
    )
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    from_bus_code: str = Field(
        min_length=1,
        max_length=80,
    )
    to_bus_code: str = Field(
        min_length=1,
        max_length=80,
    )

    branch_type: FaultBranchType

    positive_sequence_impedance: SequenceImpedanceRequest
    negative_sequence_impedance: SequenceImpedanceRequest | None = None
    zero_sequence_impedance: SequenceImpedanceRequest | None = None

    parallel_circuits: StrictInt = Field(
        default=1,
        gt=0,
    )
    in_service: StrictBool = True

    equipment_reference: str | None = Field(
        default=None,
        max_length=120,
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

    def to_domain(self) -> FaultBranchInput:
        """Convert request to immutable fault branch."""

        return FaultBranchInput(
            code=self.code,
            name=self.name,
            from_bus_code=self.from_bus_code,
            to_bus_code=self.to_bus_code,
            branch_type=self.branch_type,
            positive_sequence_impedance=(self.positive_sequence_impedance.to_domain()),
            negative_sequence_impedance=(
                self.negative_sequence_impedance.to_domain()
                if self.negative_sequence_impedance is not None
                else None
            ),
            zero_sequence_impedance=(
                self.zero_sequence_impedance.to_domain()
                if self.zero_sequence_impedance is not None
                else None
            ),
            parallel_circuits=self.parallel_circuits,
            in_service=self.in_service,
            equipment_reference=self.equipment_reference,
            notes=self.notes,
        )

    @model_validator(mode="after")
    def validate_domain_contract(self) -> Self:
        """Apply branch invariants."""

        self.to_domain()
        return self


class FaultLocationRequest(_RequestBase):
    """Fault location and fault-path impedance."""

    bus_code: str = Field(
        min_length=1,
        max_length=80,
    )
    fault_type: FaultType

    fault_resistance_ohm: ExactDecimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
    )
    fault_reactance_ohm: ExactDecimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
    )
    clearing_time_s: ExactDecimal | None = Field(
        default=None,
        gt=Decimal("0"),
    )

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    def to_domain(self) -> FaultLocationInput:
        """Convert request to immutable fault location."""

        return FaultLocationInput(
            bus_code=self.bus_code,
            fault_type=self.fault_type,
            fault_resistance_ohm=self.fault_resistance_ohm,
            fault_reactance_ohm=self.fault_reactance_ohm,
            clearing_time_s=self.clearing_time_s,
            description=self.description,
        )

    @model_validator(mode="after")
    def validate_domain_contract(self) -> Self:
        """Apply fault-location invariants."""

        self.to_domain()
        return self


class ShortCircuitStudyRequest(_RequestBase):
    """Complete validated short-circuit calculation request."""

    code: str = Field(
        min_length=1,
        max_length=80,
    )
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    calculation_case: ShortCircuitCase
    fault: FaultLocationRequest

    buses: tuple[FaultBusRequest, ...] = Field(
        min_length=1,
    )
    sources: tuple[FaultSourceRequest, ...] = Field(
        min_length=1,
    )
    branches: tuple[FaultBranchRequest, ...] = ()

    frequency_hz: ExactDecimal = Field(
        default=Decimal("50"),
        gt=Decimal("0"),
    )

    operating_state_code: str | None = Field(
        default=None,
        max_length=80,
    )

    standard_reference: str = Field(
        default="IEC 60909-0:2026",
        min_length=1,
        max_length=200,
    )
    earth_current_reference: str = Field(
        default="IEC 60909-3:2009",
        min_length=1,
        max_length=200,
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    def to_domain(self) -> ShortCircuitStudyInput:
        """Convert request to immutable fault-study input."""

        return ShortCircuitStudyInput(
            code=self.code,
            name=self.name,
            calculation_case=self.calculation_case,
            fault=self.fault.to_domain(),
            buses=tuple(bus.to_domain() for bus in self.buses),
            sources=tuple(source.to_domain() for source in self.sources),
            branches=tuple(branch.to_domain() for branch in self.branches),
            frequency_hz=self.frequency_hz,
            operating_state_code=self.operating_state_code,
            standard_reference=self.standard_reference,
            earth_current_reference=self.earth_current_reference,
            notes=self.notes,
        )

    @model_validator(mode="after")
    def validate_domain_contract(self) -> Self:
        """Apply topology and complete study-domain invariants."""

        self.to_domain()
        return self


class FaultEngineeringWarningResponse(_ResponseBase):
    """Structured engineering warning."""

    code: FaultWarningCode
    severity: FaultWarningSeverity
    message: str
    reference_code: str | None = None

    @classmethod
    def from_domain(
        cls,
        result: FaultEngineeringWarning,
    ) -> "FaultEngineeringWarningResponse":
        """Create response from domain warning."""

        return cls.model_validate(result)


class EquivalentSequenceImpedanceResponse(_ResponseBase):
    """Equivalent symmetrical-sequence impedance response."""

    sequence: FaultSequence
    available: bool
    resistance_ohm: Decimal | None
    reactance_ohm: Decimal | None
    path_reference_codes: tuple[str, ...]
    blocking_reference_codes: tuple[str, ...]

    @classmethod
    def from_domain(
        cls,
        result: EquivalentSequenceImpedanceResult,
    ) -> "EquivalentSequenceImpedanceResponse":
        """Create response from domain sequence result."""

        return cls.model_validate(result)


class FaultSourceContributionResponse(_ResponseBase):
    """Calculated or excluded source contribution."""

    source_code: str
    source_type: FaultSourceType
    representation: SourceRepresentation
    included: bool

    initial_symmetrical_current_ka: Decimal
    peak_current_ka: Decimal | None
    exclusion_reason: str | None = None

    @classmethod
    def from_domain(
        cls,
        result: FaultSourceContributionResult,
    ) -> "FaultSourceContributionResponse":
        """Create response from source contribution."""

        return cls.model_validate(result)


class ShortCircuitStudyResponse(_ResponseBase):
    """Complete short-circuit calculation response."""

    study_code: str
    study_name: str

    calculation_case: ShortCircuitCase
    fault_bus_code: str
    fault_type: FaultType

    nominal_voltage_v: Decimal
    frequency_hz: Decimal
    status: FaultResultStatus

    initial_symmetrical_short_circuit_current_ka: Decimal | None
    peak_short_circuit_current_ka: Decimal | None
    symmetrical_breaking_current_ka: Decimal | None
    steady_state_short_circuit_current_ka: Decimal | None
    thermal_equivalent_short_circuit_current_ka: Decimal | None
    earth_fault_current_ka: Decimal | None

    kappa_factor: Decimal | None
    x_r_ratio: Decimal | None
    clearing_time_s: Decimal | None

    sequence_results: tuple[EquivalentSequenceImpedanceResponse, ...]
    source_contributions: tuple[FaultSourceContributionResponse, ...]
    warnings: tuple[FaultEngineeringWarningResponse, ...]

    standard_reference: str
    earth_current_reference: str

    operating_state_code: str | None = None
    notes: str | None = None

    @classmethod
    def from_domain(
        cls,
        result: ShortCircuitStudyResult,
    ) -> "ShortCircuitStudyResponse":
        """Create API response from immutable domain result."""

        return cls.model_validate(result)


__all__ = [
    "EquivalentSequenceImpedanceResponse",
    "FaultBranchRequest",
    "FaultBusRequest",
    "FaultEngineeringWarningResponse",
    "FaultLocationRequest",
    "FaultSourceContributionResponse",
    "FaultSourceRequest",
    "SequenceImpedanceRequest",
    "ShortCircuitStudyRequest",
    "ShortCircuitStudyResponse",
]
