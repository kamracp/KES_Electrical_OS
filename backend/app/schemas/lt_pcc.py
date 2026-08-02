
"""
Pydantic schemas for LT PCC / Main Panel engineering.
KESE-S2-M10
"""

from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
)

from app.domain.electrical.distribution.lt_pcc_models import (
    LTFeederInput,
    LTFeederType,
    LTPanelFormOfSeparation,
    LTPanelInstallation,
    LTPCCSizingInput,
    LTSystemVoltage,
    LTSwitchingDevice,
    LTTripUnitType,
)
from app.domain.electrical.distribution.lt_pcc_results import (
    LTPCCSizingStatus,
    LTPCCWarningCode,
)


def _reject_float(value: object) -> object:
    """Reject binary floating-point engineering inputs."""

    if isinstance(value, float):
        raise ValueError(
            "engineering decimal values must be provided as "
            "strings, integers, or Decimal values"
        )

    return value


ExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_reject_float),
]


class _RequestBase(BaseModel):
    """Shared request configuration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class _ResponseBase(BaseModel):
    """Shared response configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class LTFeederRequest(_RequestBase):
    """LT feeder engineering request."""

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)

    feeder_type: LTFeederType
    switching_device: LTSwitchingDevice
    trip_unit_type: LTTripUnitType

    design_current_a: ExactDecimal = Field(gt=Decimal("0"))
    rated_current_a: ExactDecimal = Field(gt=Decimal("0"))

    prospective_short_circuit_current_ka: ExactDecimal = Field(
        gt=Decimal("0")
    )
    rated_ultimate_breaking_capacity_ka: ExactDecimal = Field(
        gt=Decimal("0")
    )
    rated_service_breaking_capacity_ka: ExactDecimal = Field(
        gt=Decimal("0")
    )
    rated_short_time_withstand_current_ka: ExactDecimal = Field(
        gt=Decimal("0")
    )

    number_of_poles: StrictInt = Field(default=4)
    cable_count: StrictInt = Field(default=1, gt=0)
    spare_feeder: StrictBool = False

    notes: str | None = None

    def to_domain(self) -> LTFeederInput:
        """Convert request to immutable domain record."""

        return LTFeederInput(
            code=self.code,
            name=self.name,
            feeder_type=self.feeder_type,
            switching_device=self.switching_device,
            trip_unit_type=self.trip_unit_type,
            design_current_a=self.design_current_a,
            rated_current_a=self.rated_current_a,
            prospective_short_circuit_current_ka=(
                self.prospective_short_circuit_current_ka
            ),
            rated_ultimate_breaking_capacity_ka=(
                self.rated_ultimate_breaking_capacity_ka
            ),
            rated_service_breaking_capacity_ka=(
                self.rated_service_breaking_capacity_ka
            ),
            rated_short_time_withstand_current_ka=(
                self.rated_short_time_withstand_current_ka
            ),
            number_of_poles=self.number_of_poles,
            cable_count=self.cable_count,
            spare_feeder=self.spare_feeder,
            notes=self.notes,
        )


class LTPCCSizingRequest(_RequestBase):
    """LT PCC / Main Panel engineering request."""

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)

    system_voltage: LTSystemVoltage
    frequency_hz: ExactDecimal = Field(gt=Decimal("0"))

    installation: LTPanelInstallation
    form_of_separation: LTPanelFormOfSeparation

    busbar_rated_current_a: ExactDecimal = Field(gt=Decimal("0"))
    busbar_short_time_withstand_current_ka: ExactDecimal = Field(
        gt=Decimal("0")
    )
    busbar_peak_withstand_current_ka: ExactDecimal = Field(
        gt=Decimal("0")
    )

    neutral_bus_rating_percent: ExactDecimal = Field(
        gt=Decimal("0")
    )
    earth_bus_rating_percent: ExactDecimal = Field(
        gt=Decimal("0")
    )

    feeders: tuple[LTFeederRequest, ...] = Field(min_length=1)

    bus_sections: StrictInt = Field(default=1, gt=0)
    bus_couplers: StrictInt = Field(default=0, ge=0)
    spare_feeders: StrictInt = Field(default=0, ge=0)

    ip_rating: str = Field(
        default="IP42",
        min_length=1,
        max_length=20,
    )

    apfc_required: StrictBool = False
    metering_required: StrictBool = True
    remote_operation_required: StrictBool = False

    notes: str | None = None

    def to_domain(self) -> LTPCCSizingInput:
        """Convert request to immutable domain record."""

        return LTPCCSizingInput(
            code=self.code,
            name=self.name,
            system_voltage=self.system_voltage,
            frequency_hz=self.frequency_hz,
            installation=self.installation,
            form_of_separation=self.form_of_separation,
            busbar_rated_current_a=self.busbar_rated_current_a,
            busbar_short_time_withstand_current_ka=(
                self.busbar_short_time_withstand_current_ka
            ),
            busbar_peak_withstand_current_ka=(
                self.busbar_peak_withstand_current_ka
            ),
            neutral_bus_rating_percent=(
                self.neutral_bus_rating_percent
            ),
            earth_bus_rating_percent=(
                self.earth_bus_rating_percent
            ),
            feeders=tuple(
                feeder.to_domain()
                for feeder in self.feeders
            ),
            bus_sections=self.bus_sections,
            bus_couplers=self.bus_couplers,
            spare_feeders=self.spare_feeders,
            ip_rating=self.ip_rating,
            apfc_required=self.apfc_required,
            metering_required=self.metering_required,
            remote_operation_required=(
                self.remote_operation_required
            ),
            notes=self.notes,
        )


class LTPCCWarningResponse(_ResponseBase):
    """Structured LT PCC warning response."""

    code: LTPCCWarningCode
    message: str


class LTFeederResponse(_ResponseBase):
    """Calculated LT feeder response."""

    code: str
    name: str

    feeder_type: LTFeederType
    switching_device: LTSwitchingDevice
    trip_unit_type: LTTripUnitType

    design_current_a: Decimal
    rated_current_a: Decimal
    loading_percent: Decimal
    spare_current_capacity_a: Decimal

    prospective_short_circuit_current_ka: Decimal

    rated_ultimate_breaking_capacity_ka: Decimal
    icu_margin_ka: Decimal

    rated_service_breaking_capacity_ka: Decimal
    ics_margin_ka: Decimal

    rated_short_time_withstand_current_ka: Decimal
    icw_margin_ka: Decimal

    number_of_poles: int
    cable_count: int
    spare_feeder: bool

    warnings: tuple[LTPCCWarningResponse, ...]


class LTPCCSizingResponse(_ResponseBase):
    """Calculated LT PCC / Main Panel response."""

    code: str
    name: str

    system_voltage: LTSystemVoltage
    installation: LTPanelInstallation
    form_of_separation: LTPanelFormOfSeparation

    total_feeders: int
    active_feeders: int
    spare_feeders: int

    bus_sections: int
    bus_couplers: int

    aggregate_design_current_a: Decimal
    maximum_feeder_rated_current_a: Decimal

    busbar_rated_current_a: Decimal
    busbar_loading_percent: Decimal
    busbar_spare_capacity_a: Decimal

    maximum_fault_current_ka: Decimal
    busbar_short_time_withstand_current_ka: Decimal
    busbar_fault_margin_ka: Decimal

    busbar_peak_withstand_current_ka: Decimal

    neutral_bus_rating_percent: Decimal
    earth_bus_rating_percent: Decimal

    apfc_required: bool
    metering_required: bool
    remote_operation_required: bool

    feeder_results: tuple[LTFeederResponse, ...]

    status: LTPCCSizingStatus
    warnings: tuple[LTPCCWarningResponse, ...]


__all__ = [
    "LTFeederRequest",
    "LTFeederResponse",
    "LTPCCSizingRequest",
    "LTPCCSizingResponse",
    "LTPCCWarningResponse",
]
