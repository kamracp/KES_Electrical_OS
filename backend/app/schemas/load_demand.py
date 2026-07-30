"""
Pydantic schemas for electrical load and demand calculations.
KESE-S2-M2
"""

from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    model_validator,
)

from app.domain.electrical.loads.models import (
    LoadGroupInput,
    LoadInput,
    LoadScenario,
    PhaseSystem,
    PowerBasis,
)
from app.domain.electrical.loads.results import (
    CalculationStatus,
    LoadWarningCode,
)


def _reject_float(value: object) -> object:
    """Reject binary floating-point engineering inputs."""

    if isinstance(value, float):
        raise ValueError(
            "engineering decimal values must be provided as "
            "strings, integers, or Decimal values"
        )

    return value

type ExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
]


class _RequestBase(BaseModel):
    """Shared API request configuration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class _ResponseBase(BaseModel):
    """Shared API response configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class LoadCalculationRequest(_RequestBase):
    """API request for calculating one electrical load."""

    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    quantity: StrictInt = Field(
        gt=0,
    )
    rated_power_kw: ExactDecimal = Field(
        gt=Decimal("0"),
        max_digits=38,
        decimal_places=18,
    )
    phase_system: PhaseSystem
    voltage_v: ExactDecimal = Field(
        gt=Decimal("0"),
        max_digits=38,
        decimal_places=18,
    )
    power_factor: ExactDecimal = Field(
        default=Decimal("1"),
        gt=Decimal("0"),
        le=Decimal("1"),
        max_digits=38,
        decimal_places=18,
    )
    efficiency: ExactDecimal = Field(
        default=Decimal("1"),
        gt=Decimal("0"),
        le=Decimal("1"),
        max_digits=38,
        decimal_places=18,
    )
    utilization_factor: ExactDecimal = Field(
        default=Decimal("1"),
        ge=Decimal("0"),
        le=Decimal("1"),
        max_digits=38,
        decimal_places=18,
    )
    demand_factor: ExactDecimal = Field(
        default=Decimal("1"),
        ge=Decimal("0"),
        le=Decimal("1"),
        max_digits=38,
        decimal_places=18,
    )
    scenario: LoadScenario = LoadScenario.NORMAL
    power_basis: PowerBasis = PowerBasis.ELECTRICAL_INPUT
    notes: str | None = None

    @model_validator(mode="after")
    def validate_phase_configuration(
        self,
    ) -> "LoadCalculationRequest":
        """Validate phase-specific input requirements."""

        if (
            self.phase_system is PhaseSystem.DC
            and self.power_factor != Decimal("1")
        ):
            raise ValueError(
                "DC loads must use a power_factor of 1"
            )

        return self

    def to_domain(self) -> LoadInput:
        """Convert the validated API request to a domain record."""

        return LoadInput(
            code=self.code,
            name=self.name,
            quantity=self.quantity,
            rated_power_kw=self.rated_power_kw,
            phase_system=self.phase_system,
            voltage_v=self.voltage_v,
            power_factor=self.power_factor,
            efficiency=self.efficiency,
            utilization_factor=self.utilization_factor,
            demand_factor=self.demand_factor,
            scenario=self.scenario,
            power_basis=self.power_basis,
            notes=self.notes,
        )


class LoadGroupCalculationRequest(_RequestBase):
    """API request for calculating an electrical load group."""

    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    loads: tuple[LoadCalculationRequest, ...] = Field(
        min_length=1,
    )
    coincidence_factor: ExactDecimal = Field(
        default=Decimal("1"),
        ge=Decimal("0"),
        le=Decimal("1"),
        max_digits=38,
        decimal_places=18,
    )

    def to_domain(self) -> LoadGroupInput:
        """Convert the validated API request to a domain group."""

        return LoadGroupInput(
            code=self.code,
            name=self.name,
            loads=tuple(
                load.to_domain()
                for load in self.loads
            ),
            coincidence_factor=self.coincidence_factor,
        )


class CalculationWarningResponse(_ResponseBase):
    """Structured warning returned by the calculation API."""

    code: LoadWarningCode
    message: str


class LoadCalculationResponse(_ResponseBase):
    """API response for one calculated electrical load."""

    load_code: str
    load_name: str
    scenario: LoadScenario
    phase_system: PhaseSystem
    connected_power_kw: Decimal
    utilized_power_kw: Decimal
    demand_power_kw: Decimal
    apparent_power_kva: Decimal
    reactive_power_kvar: Decimal
    design_current_a: Decimal
    status: CalculationStatus
    warnings: tuple[CalculationWarningResponse, ...]


class LoadGroupCalculationResponse(_ResponseBase):
    """API response for an aggregated load group."""

    group_code: str
    group_name: str
    coincidence_factor: Decimal
    connected_power_kw: Decimal
    pre_coincidence_demand_kw: Decimal
    demand_power_kw: Decimal
    apparent_power_kva: Decimal
    reactive_power_kvar: Decimal
    load_results: tuple[LoadCalculationResponse, ...]
    status: CalculationStatus
    warnings: tuple[CalculationWarningResponse, ...]


__all__ = [
    "CalculationWarningResponse",
    "LoadCalculationRequest",
    "LoadCalculationResponse",
    "LoadGroupCalculationRequest",
    "LoadGroupCalculationResponse",
]