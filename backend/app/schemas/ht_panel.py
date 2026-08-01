"""
Pydantic schemas for HT panel engineering.
KESE-S2-M9
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

from app.domain.electrical.sources.ht_panel_models import (
    HTFeederInput,
    HTFeederType,
    HTPanelConstruction,
    HTPanelInstallation,
    HTPanelSizingInput,
    HTRelayFunction,
    HTSwitchingDevice,
    HTSystemVoltage,
)
from app.domain.electrical.sources.ht_panel_results import (
    HTPanelSizingStatus,
    HTPanelWarningCode,
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


class HTFeederRequest(_RequestBase):
    """HT feeder engineering request."""

    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    feeder_type: HTFeederType
    switching_device: HTSwitchingDevice

    design_current_a: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    prospective_short_circuit_current_ka: ExactDecimal = Field(
        gt=Decimal("0"),
    )

    rated_normal_current_a: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    rated_short_circuit_breaking_current_ka: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    rated_short_time_withstand_current_ka: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    short_time_withstand_duration_s: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    rated_peak_withstand_current_ka: ExactDecimal = Field(
        gt=Decimal("0"),
    )

    ct_primary_current_a: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    ct_secondary_current_a: ExactDecimal = Field(
        default=Decimal("1"),
        gt=Decimal("0"),
    )
    ct_protection_class: str = Field(
        default="5P20",
        min_length=1,
        max_length=50,
    )
    ct_metering_class: str = Field(
        default="0.5",
        min_length=1,
        max_length=50,
    )

    relay_functions: tuple[HTRelayFunction, ...] = Field(
        default=(
            HTRelayFunction.OVERCURRENT,
            HTRelayFunction.EARTH_FAULT,
        ),
        min_length=1,
    )

    cable_count: StrictInt = Field(
        default=1,
        gt=0,
    )
    spare_feeder: StrictBool = False
    notes: str | None = None

    def to_domain(self) -> HTFeederInput:
        """Convert request to immutable domain record."""

        return HTFeederInput(
            code=self.code,
            name=self.name,
            feeder_type=self.feeder_type,
            switching_device=self.switching_device,
            design_current_a=self.design_current_a,
            prospective_short_circuit_current_ka=(
                self.prospective_short_circuit_current_ka
            ),
            rated_normal_current_a=self.rated_normal_current_a,
            rated_short_circuit_breaking_current_ka=(
                self.rated_short_circuit_breaking_current_ka
            ),
            rated_short_time_withstand_current_ka=(
                self.rated_short_time_withstand_current_ka
            ),
            short_time_withstand_duration_s=(
                self.short_time_withstand_duration_s
            ),
            rated_peak_withstand_current_ka=(
                self.rated_peak_withstand_current_ka
            ),
            ct_primary_current_a=self.ct_primary_current_a,
            ct_secondary_current_a=self.ct_secondary_current_a,
            ct_protection_class=self.ct_protection_class,
            ct_metering_class=self.ct_metering_class,
            relay_functions=self.relay_functions,
            cable_count=self.cable_count,
            spare_feeder=self.spare_feeder,
            notes=self.notes,
        )


class HTPanelSizingRequest(_RequestBase):
    """HT panel engineering request."""

    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    system_voltage: HTSystemVoltage
    highest_system_voltage_kv: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    frequency_hz: ExactDecimal = Field(
        gt=Decimal("0"),
    )

    installation: HTPanelInstallation
    construction: HTPanelConstruction

    busbar_rated_current_a: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    busbar_short_time_withstand_current_ka: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    busbar_short_time_duration_s: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    busbar_peak_withstand_current_ka: ExactDecimal = Field(
        gt=Decimal("0"),
    )

    rated_insulation_level_kv: ExactDecimal = Field(
        gt=Decimal("0"),
    )
    lightning_impulse_withstand_voltage_kvp: ExactDecimal = Field(
        gt=Decimal("0"),
    )

    feeders: tuple[HTFeederRequest, ...] = Field(
        min_length=1,
    )

    bus_sections: StrictInt = Field(
        default=1,
        gt=0,
    )
    bus_couplers: StrictInt = Field(
        default=0,
        ge=0,
    )
    spare_feeders: StrictInt = Field(
        default=0,
        ge=0,
    )

    indoor_ip_rating: str = Field(
        default="IP4X",
        min_length=1,
        max_length=20,
    )
    outdoor_ip_rating: str = Field(
        default="IP54",
        min_length=1,
        max_length=20,
    )

    earthing_switch_required: StrictBool = True
    arc_classification_required: StrictBool = True
    remote_operation_required: StrictBool = False

    notes: str | None = None

    def to_domain(self) -> HTPanelSizingInput:
        """Convert request to immutable domain record."""

        return HTPanelSizingInput(
            code=self.code,
            name=self.name,
            system_voltage=self.system_voltage,
            highest_system_voltage_kv=(
                self.highest_system_voltage_kv
            ),
            frequency_hz=self.frequency_hz,
            installation=self.installation,
            construction=self.construction,
            busbar_rated_current_a=self.busbar_rated_current_a,
            busbar_short_time_withstand_current_ka=(
                self.busbar_short_time_withstand_current_ka
            ),
            busbar_short_time_duration_s=(
                self.busbar_short_time_duration_s
            ),
            busbar_peak_withstand_current_ka=(
                self.busbar_peak_withstand_current_ka
            ),
            rated_insulation_level_kv=(
                self.rated_insulation_level_kv
            ),
            lightning_impulse_withstand_voltage_kvp=(
                self.lightning_impulse_withstand_voltage_kvp
            ),
            feeders=tuple(
                feeder.to_domain()
                for feeder in self.feeders
            ),
            bus_sections=self.bus_sections,
            bus_couplers=self.bus_couplers,
            spare_feeders=self.spare_feeders,
            indoor_ip_rating=self.indoor_ip_rating,
            outdoor_ip_rating=self.outdoor_ip_rating,
            earthing_switch_required=(
                self.earthing_switch_required
            ),
            arc_classification_required=(
                self.arc_classification_required
            ),
            remote_operation_required=(
                self.remote_operation_required
            ),
            notes=self.notes,
        )


class HTPanelWarningResponse(_ResponseBase):
    """Structured HT panel warning response."""

    code: HTPanelWarningCode
    message: str


class HTFeederResponse(_ResponseBase):
    """Calculated HT feeder response."""

    code: str
    name: str

    feeder_type: HTFeederType
    switching_device: HTSwitchingDevice

    design_current_a: Decimal
    rated_normal_current_a: Decimal
    current_loading_percent: Decimal

    prospective_short_circuit_current_ka: Decimal
    rated_short_circuit_breaking_current_ka: Decimal
    breaking_capacity_margin_ka: Decimal

    rated_short_time_withstand_current_ka: Decimal
    short_time_withstand_margin_ka: Decimal
    short_time_withstand_duration_s: Decimal

    rated_peak_withstand_current_ka: Decimal

    ct_primary_current_a: Decimal
    ct_secondary_current_a: Decimal
    ct_ratio: str
    ct_margin_a: Decimal

    relay_functions: tuple[HTRelayFunction, ...]

    warnings: tuple[HTPanelWarningResponse, ...]


class HTPanelSizingResponse(_ResponseBase):
    """Calculated HT panel response."""

    code: str
    name: str

    system_voltage: HTSystemVoltage
    installation: HTPanelInstallation
    construction: HTPanelConstruction

    total_feeders: int
    active_feeders: int
    spare_feeders: int

    bus_sections: int
    bus_couplers: int

    maximum_feeder_current_a: Decimal
    aggregate_design_current_a: Decimal

    busbar_rated_current_a: Decimal
    busbar_loading_percent: Decimal
    busbar_spare_capacity_a: Decimal

    maximum_fault_current_ka: Decimal
    busbar_short_time_withstand_current_ka: Decimal
    busbar_fault_margin_ka: Decimal

    busbar_peak_withstand_current_ka: Decimal

    feeder_results: tuple[HTFeederResponse, ...]

    status: HTPanelSizingStatus
    warnings: tuple[HTPanelWarningResponse, ...]


__all__ = [
    "HTFeederRequest",
    "HTFeederResponse",
    "HTPanelSizingRequest",
    "HTPanelSizingResponse",
    "HTPanelWarningResponse",
]
