"""
Pydantic schemas for transformer source-sizing calculations.
KESE-S2-M5
"""

from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    model_validator,
)

from app.domain.electrical.jurisdiction.jurisdiction_models import (
    JurisdictionProfile,
)
from app.domain.electrical.loads.models import LoadScenario
from app.domain.electrical.sources.models import (
    TransformerRedundancyMode,
    TransformerSizingInput,
)
from app.domain.electrical.sources.results import (
    TransformerSizingResult,
    TransformerSizingStatus,
    TransformerSizingWarningCode,
)


def _reject_float(value: object) -> object:
    """Reject binary floating-point engineering inputs."""

    if isinstance(value, float):
        raise ValueError(
            "engineering decimal values must be provided as strings, integers, or Decimal values"
        )

    return value


type ExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
]

type PositiveExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
    Field(
        gt=Decimal("0"),
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
    """Shared transformer-sizing request configuration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class _ResponseBase(BaseModel):
    """Shared transformer-sizing response configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class TransformerSizingRequest(_RequestBase):
    """API request for transformer source sizing."""

    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    demand_power_kw: PositiveExactDecimal
    demand_power_factor: RatioExactDecimal

    available_unit_ratings_kva: tuple[
        PositiveExactDecimal,
        ...,
    ] = Field(
        min_length=1,
    )

    # A blank factor means NOT ESTABLISHED and reaches the engine as None: it sizes
    # with 1, names the factor in a warning and reports REVIEW_REQUIRED (A16 (a)).
    # The schema never fills a default in its place.
    future_growth_factor: FactorExactDecimal | None = None
    design_margin_factor: FactorExactDecimal | None = None

    ambient_derating_factor: RatioExactDecimal | None = None
    altitude_derating_factor: RatioExactDecimal | None = None
    harmonic_derating_factor: RatioExactDecimal | None = None

    duty_units: StrictInt = Field(
        default=1,
        gt=0,
    )
    standby_units: StrictInt = Field(
        default=0,
        ge=0,
    )

    redundancy_mode: TransformerRedundancyMode = TransformerRedundancyMode.NONE
    scenario: LoadScenario = LoadScenario.NORMAL

    # The sizing itself has no profile-dependent value; the profile is carried for
    # the result, the run record and the design basis of the project revision.
    jurisdiction_profile: JurisdictionProfile = JurisdictionProfile.IN

    notes: str | None = None

    @model_validator(mode="after")
    def validate_rating_schedule_and_redundancy(
        self,
    ) -> Self:
        """Validate controlled ratings and redundancy arrangement."""

        if len(self.available_unit_ratings_kva) != len(set(self.available_unit_ratings_kva)):
            raise ValueError("available transformer ratings must be unique")

        if self.available_unit_ratings_kva != tuple(sorted(self.available_unit_ratings_kva)):
            raise ValueError("available transformer ratings must be in ascending order")

        if self.redundancy_mode is TransformerRedundancyMode.NONE and self.standby_units != 0:
            raise ValueError("NONE redundancy requires standby_units to be 0")

        if self.redundancy_mode is TransformerRedundancyMode.N_PLUS_1 and self.standby_units != 1:
            raise ValueError("N_PLUS_1 redundancy requires exactly one standby unit")

        if (
            self.redundancy_mode is TransformerRedundancyMode.TWO_N
            and self.standby_units != self.duty_units
        ):
            raise ValueError("TWO_N redundancy requires standby_units to equal duty_units")

        return self

    def to_domain(self) -> TransformerSizingInput:
        """Convert the validated API request to a domain record."""

        return TransformerSizingInput(
            code=self.code,
            name=self.name,
            demand_power_kw=self.demand_power_kw,
            demand_power_factor=self.demand_power_factor,
            available_unit_ratings_kva=(self.available_unit_ratings_kva),
            future_growth_factor=self.future_growth_factor,
            design_margin_factor=self.design_margin_factor,
            ambient_derating_factor=(self.ambient_derating_factor),
            altitude_derating_factor=(self.altitude_derating_factor),
            harmonic_derating_factor=(self.harmonic_derating_factor),
            duty_units=self.duty_units,
            standby_units=self.standby_units,
            redundancy_mode=self.redundancy_mode,
            scenario=self.scenario,
            notes=self.notes,
        )


class TransformerSizingWarningResponse(_ResponseBase):
    """Structured warning returned by the sizing API."""

    code: TransformerSizingWarningCode
    message: str


class TransformerSizingResponse(_ResponseBase):
    """API response for a transformer-sizing calculation."""

    code: str
    name: str

    scenario: LoadScenario
    redundancy_mode: TransformerRedundancyMode

    demand_power_kw: Decimal
    demand_power_factor: Decimal
    base_demand_kva: Decimal

    future_growth_factor: Decimal
    future_demand_kva: Decimal

    design_margin_factor: Decimal
    design_required_kva: Decimal

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
    loading_percent: Decimal | None

    status: TransformerSizingStatus

    warnings: tuple[
        TransformerSizingWarningResponse,
        ...,
    ]

    jurisdiction_profile: JurisdictionProfile

    @classmethod
    def from_domain(
        cls,
        result: TransformerSizingResult,
        *,
        jurisdiction_profile: JurisdictionProfile,
    ) -> Self:
        """
        Create the response from the domain result and the requested profile.

        The sizing engine carries no jurisdiction profile, so the profile of the
        request is echoed here rather than read from the result.
        """

        return cls(
            code=result.code,
            name=result.name,
            scenario=result.scenario,
            redundancy_mode=result.redundancy_mode,
            demand_power_kw=result.demand_power_kw,
            demand_power_factor=result.demand_power_factor,
            base_demand_kva=result.base_demand_kva,
            future_growth_factor=result.future_growth_factor,
            future_demand_kva=result.future_demand_kva,
            design_margin_factor=result.design_margin_factor,
            design_required_kva=result.design_required_kva,
            combined_derating_factor=result.combined_derating_factor,
            required_nameplate_capacity_kva=(result.required_nameplate_capacity_kva),
            duty_units=result.duty_units,
            standby_units=result.standby_units,
            total_units=result.total_units,
            required_unit_rating_kva=result.required_unit_rating_kva,
            selected_unit_rating_kva=result.selected_unit_rating_kva,
            installed_nameplate_capacity_kva=(result.installed_nameplate_capacity_kva),
            derated_duty_capacity_kva=result.derated_duty_capacity_kva,
            spare_derated_capacity_kva=result.spare_derated_capacity_kva,
            loading_percent=result.loading_percent,
            status=result.status,
            warnings=tuple(
                TransformerSizingWarningResponse.model_validate(warning)
                for warning in result.warnings
            ),
            jurisdiction_profile=jurisdiction_profile,
        )


__all__ = [
    "TransformerSizingRequest",
    "TransformerSizingResponse",
    "TransformerSizingWarningResponse",
]
