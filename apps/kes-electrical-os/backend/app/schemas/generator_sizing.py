"""
Pydantic schemas for generator source-sizing calculations.
KESE-S2-M7
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

from kes_electrical_core.loads.models import LoadScenario
from kes_electrical_core.sources.generator_models import (
    GeneratorDutyClass,
    GeneratorRedundancyMode,
    GeneratorSizingInput,
)
from kes_electrical_core.sources.generator_results import (
    GeneratorSizingStatus,
    GeneratorSizingWarningCode,
)


def _reject_float(value: object) -> object:
    """Reject binary floating-point engineering inputs."""

    if isinstance(value, float):
        raise ValueError(
            "engineering decimal values must be provided as "
            "strings, integers, or Decimal values"
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

type FactorExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
    Field(
        ge=Decimal("1"),
        max_digits=38,
        decimal_places=18,
    ),
]


class _RequestBase(BaseModel):
    """Shared generator-sizing request configuration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class _ResponseBase(BaseModel):
    """Shared generator-sizing response configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class GeneratorSizingRequest(_RequestBase):
    """API request for generator source sizing."""

    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    steady_state_demand_kw: PositiveExactDecimal
    steady_state_power_factor: RatioExactDecimal

    transient_step_load_kva: NonNegativeExactDecimal = Decimal("0")
    transient_allowance_factor: FactorExactDecimal = Decimal("1")

    future_growth_factor: FactorExactDecimal = Decimal("1")
    design_margin_factor: FactorExactDecimal = Decimal("1.10")

    ambient_derating_factor: RatioExactDecimal = Decimal("1")
    altitude_derating_factor: RatioExactDecimal = Decimal("1")

    available_unit_ratings_kva: tuple[
        PositiveExactDecimal,
        ...,
    ] = Field(
        min_length=1,
    )

    duty_units: StrictInt = Field(
        default=1,
        gt=0,
    )
    standby_units: StrictInt = Field(
        default=0,
        ge=0,
    )

    duty_class: GeneratorDutyClass = GeneratorDutyClass.STANDBY

    redundancy_mode: GeneratorRedundancyMode = (
        GeneratorRedundancyMode.NONE
    )

    scenario: LoadScenario = LoadScenario.EMERGENCY

    notes: str | None = None

    @model_validator(mode="after")
    def validate_rating_schedule_and_redundancy(
        self,
    ) -> "GeneratorSizingRequest":
        """Validate controlled ratings and redundancy arrangement."""

        if len(
            self.available_unit_ratings_kva
        ) != len(set(self.available_unit_ratings_kva)):
            raise ValueError(
                "available generator ratings must be unique"
            )

        if self.available_unit_ratings_kva != tuple(
            sorted(self.available_unit_ratings_kva)
        ):
            raise ValueError(
                "available generator ratings "
                "must be in ascending order"
            )

        if (
            self.redundancy_mode
            is GeneratorRedundancyMode.NONE
            and self.standby_units != 0
        ):
            raise ValueError(
                "NONE redundancy requires "
                "standby_units to be 0"
            )

        if (
            self.redundancy_mode
            is GeneratorRedundancyMode.N_PLUS_1
            and self.standby_units != 1
        ):
            raise ValueError(
                "N_PLUS_1 redundancy requires "
                "exactly one standby unit"
            )

        if (
            self.redundancy_mode
            is GeneratorRedundancyMode.TWO_N
            and self.standby_units != self.duty_units
        ):
            raise ValueError(
                "TWO_N redundancy requires standby_units "
                "to equal duty_units"
            )

        return self

    def to_domain(self) -> GeneratorSizingInput:
        """Convert the validated API request to a domain record."""

        return GeneratorSizingInput(
            code=self.code,
            name=self.name,
            steady_state_demand_kw=(
                self.steady_state_demand_kw
            ),
            steady_state_power_factor=(
                self.steady_state_power_factor
            ),
            transient_step_load_kva=(
                self.transient_step_load_kva
            ),
            transient_allowance_factor=(
                self.transient_allowance_factor
            ),
            future_growth_factor=self.future_growth_factor,
            design_margin_factor=self.design_margin_factor,
            ambient_derating_factor=(
                self.ambient_derating_factor
            ),
            altitude_derating_factor=(
                self.altitude_derating_factor
            ),
            available_unit_ratings_kva=(
                self.available_unit_ratings_kva
            ),
            duty_units=self.duty_units,
            standby_units=self.standby_units,
            duty_class=self.duty_class,
            redundancy_mode=self.redundancy_mode,
            scenario=self.scenario,
            notes=self.notes,
        )


class GeneratorSizingWarningResponse(_ResponseBase):
    """Structured warning returned by the sizing API."""

    code: GeneratorSizingWarningCode
    message: str


class GeneratorSizingResponse(_ResponseBase):
    """API response for a generator-sizing calculation."""

    code: str
    name: str

    scenario: LoadScenario
    duty_class: GeneratorDutyClass
    redundancy_mode: GeneratorRedundancyMode

    steady_state_demand_kw: Decimal
    steady_state_power_factor: Decimal
    steady_state_demand_kva: Decimal

    future_growth_factor: Decimal
    future_steady_state_kva: Decimal

    design_margin_factor: Decimal
    steady_state_required_kva: Decimal

    transient_step_load_kva: Decimal
    transient_allowance_factor: Decimal
    transient_additional_kva: Decimal
    transient_required_kva: Decimal

    governing_required_kva: Decimal

    combined_derating_factor: Decimal
    required_nameplate_capacity_kva: Decimal

    duty_units: int
    standby_units: int
    total_units: int

    required_unit_rating_kva: Decimal
    selected_unit_rating_kva: Decimal | None

    installed_nameplate_capacity_kva: Decimal | None
    derated_duty_capacity_kva: Decimal | None
    spare_derated_capacity_kva: Decimal | None
    steady_state_loading_percent: Decimal | None

    status: GeneratorSizingStatus

    warnings: tuple[
        GeneratorSizingWarningResponse,
        ...,
    ]


__all__ = [
    "GeneratorSizingRequest",
    "GeneratorSizingResponse",
    "GeneratorSizingWarningResponse",
]
