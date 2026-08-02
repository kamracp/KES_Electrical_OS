"""
Unit tests for LT PCC / Main Panel domain models.
KESE-S2-M10
"""

from decimal import Decimal

import pytest

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


def make_feeder(
    **overrides: object,
) -> LTFeederInput:
    values: dict[str, object] = {
        "code": "TR-IN-01",
        "name": "Transformer Incomer",
        "feeder_type": LTFeederType.TRANSFORMER_INCOMER,
        "switching_device": LTSwitchingDevice.ACB,
        "trip_unit_type": LTTripUnitType.ELECTRONIC_LSIG,
        "design_current_a": Decimal("1400"),
        "rated_current_a": Decimal("1600"),
        "prospective_short_circuit_current_ka": Decimal("50"),
        "rated_ultimate_breaking_capacity_ka": Decimal("65"),
        "rated_service_breaking_capacity_ka": Decimal("65"),
        "rated_short_time_withstand_current_ka": Decimal("65"),
        "number_of_poles": 4,
        "cable_count": 4,
        "spare_feeder": False,
    }

    values.update(overrides)

    return LTFeederInput(**values)


def make_panel(
    **overrides: object,
) -> LTPCCSizingInput:
    values: dict[str, object] = {
        "code": "PCC-001",
        "name": "Main LT PCC",
        "system_voltage": LTSystemVoltage.V_415,
        "frequency_hz": Decimal("50"),
        "installation": LTPanelInstallation.INDOOR,
        "form_of_separation": LTPanelFormOfSeparation.FORM_4B,
        "busbar_rated_current_a": Decimal("2500"),
        "busbar_short_time_withstand_current_ka": Decimal("65"),
        "busbar_peak_withstand_current_ka": Decimal("143"),
        "neutral_bus_rating_percent": Decimal("100"),
        "earth_bus_rating_percent": Decimal("50"),
        "feeders": (
            make_feeder(),
        ),
        "bus_sections": 1,
        "bus_couplers": 0,
        "spare_feeders": 1,
        "ip_rating": "IP42",
        "apfc_required": True,
        "metering_required": True,
        "remote_operation_required": False,
    }

    values.update(overrides)

    return LTPCCSizingInput(**values)


@pytest.mark.unit
def test_create_valid_lt_feeder() -> None:
    feeder = make_feeder()

    assert feeder.code == "TR-IN-01"
    assert feeder.feeder_type is LTFeederType.TRANSFORMER_INCOMER
    assert feeder.switching_device is LTSwitchingDevice.ACB
    assert feeder.trip_unit_type is LTTripUnitType.ELECTRONIC_LSIG


@pytest.mark.unit
def test_lt_feeder_text_is_trimmed() -> None:
    feeder = make_feeder(
        code="  TR-IN-01  ",
        name="  Transformer Incomer  ",
        notes="  Approved feeder  ",
    )

    assert feeder.code == "TR-IN-01"
    assert feeder.name == "Transformer Incomer"
    assert feeder.notes == "Approved feeder"


@pytest.mark.unit
def test_feeder_rating_below_design_current_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="rated_current_a must not be below",
    ):
        make_feeder(
            design_current_a=Decimal("1800"),
            rated_current_a=Decimal("1600"),
        )


@pytest.mark.unit
def test_icu_below_fault_level_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="ultimate breaking capacity must not be below",
    ):
        make_feeder(
            prospective_short_circuit_current_ka=Decimal("70"),
            rated_ultimate_breaking_capacity_ka=Decimal("65"),
        )


@pytest.mark.unit
def test_ics_above_icu_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="service breaking capacity must not exceed",
    ):
        make_feeder(
            rated_ultimate_breaking_capacity_ka=Decimal("50"),
            rated_service_breaking_capacity_ka=Decimal("65"),
        )


@pytest.mark.unit
def test_icw_below_fault_level_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="short-time withstand current must not be below",
    ):
        make_feeder(
            prospective_short_circuit_current_ka=Decimal("50"),
            rated_short_time_withstand_current_ka=Decimal("40"),
        )


@pytest.mark.unit
def test_invalid_pole_count_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="number_of_poles must be 2, 3 or 4",
    ):
        make_feeder(
            number_of_poles=1,
        )


@pytest.mark.unit
def test_create_valid_lt_pcc() -> None:
    panel = make_panel()

    assert panel.code == "PCC-001"
    assert panel.system_voltage is LTSystemVoltage.V_415
    assert panel.form_of_separation is LTPanelFormOfSeparation.FORM_4B
    assert panel.apfc_required is True


@pytest.mark.unit
def test_duplicate_feeder_codes_are_rejected() -> None:
    first = make_feeder(code="FDR-01")
    second = make_feeder(code="FDR-01")

    with pytest.raises(
        ValueError,
        match="LT feeder codes must be unique",
    ):
        make_panel(
            feeders=(first, second),
        )


@pytest.mark.unit
def test_busbar_current_below_feeder_rating_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="busbar_rated_current_a must not be below",
    ):
        make_panel(
            busbar_rated_current_a=Decimal("1250"),
        )


@pytest.mark.unit
def test_busbar_fault_rating_below_feeder_fault_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="busbar short-time withstand current must not be below",
    ):
        make_panel(
            busbar_short_time_withstand_current_ka=Decimal("40"),
        )


@pytest.mark.unit
def test_multiple_bus_sections_require_coupler() -> None:
    with pytest.raises(
        ValueError,
        match="multiple bus sections require",
    ):
        make_panel(
            bus_sections=2,
            bus_couplers=0,
        )


@pytest.mark.unit
def test_single_bus_section_rejects_coupler() -> None:
    with pytest.raises(
        ValueError,
        match="single bus section cannot have",
    ):
        make_panel(
            bus_sections=1,
            bus_couplers=1,
        )


@pytest.mark.unit
def test_valid_two_section_lt_pcc() -> None:
    panel = make_panel(
        bus_sections=2,
        bus_couplers=1,
    )

    assert panel.bus_sections == 2
    assert panel.bus_couplers == 1
