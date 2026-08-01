"""
Unit tests for HT panel engineering domain models.
KESE-S2-M9
"""

from decimal import Decimal

import pytest

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


def make_feeder(
    *,
    code: str = "HT-IN-01",
    feeder_type: HTFeederType = HTFeederType.INCOMER,
) -> HTFeederInput:
    return HTFeederInput(
        code=code,
        name="Main HT Incomer",
        feeder_type=feeder_type,
        switching_device=HTSwitchingDevice.VCB,
        design_current_a=Decimal("400"),
        prospective_short_circuit_current_ka=Decimal("20"),
        rated_normal_current_a=Decimal("630"),
        rated_short_circuit_breaking_current_ka=Decimal("25"),
        rated_short_time_withstand_current_ka=Decimal("25"),
        short_time_withstand_duration_s=Decimal("3"),
        rated_peak_withstand_current_ka=Decimal("63"),
        ct_primary_current_a=Decimal("600"),
        ct_secondary_current_a=Decimal("1"),
        relay_functions=(
            HTRelayFunction.OVERCURRENT,
            HTRelayFunction.EARTH_FAULT,
        ),
    )


def make_panel(
    **overrides: object,
) -> HTPanelSizingInput:
    values: dict[str, object] = {
        "code": "HTP-001",
        "name": "11 kV Main HT Panel",
        "system_voltage": HTSystemVoltage.KV_11,
        "highest_system_voltage_kv": Decimal("12"),
        "frequency_hz": Decimal("50"),
        "installation": HTPanelInstallation.INDOOR,
        "construction": HTPanelConstruction.METAL_CLAD,
        "busbar_rated_current_a": Decimal("1250"),
        "busbar_short_time_withstand_current_ka": Decimal("25"),
        "busbar_short_time_duration_s": Decimal("3"),
        "busbar_peak_withstand_current_ka": Decimal("63"),
        "rated_insulation_level_kv": Decimal("28"),
        "lightning_impulse_withstand_voltage_kvp": Decimal("75"),
        "feeders": (
            make_feeder(),
        ),
        "bus_sections": 1,
        "bus_couplers": 0,
        "spare_feeders": 1,
    }

    values.update(overrides)

    return HTPanelSizingInput(**values)


@pytest.mark.unit
def test_create_valid_ht_feeder() -> None:
    feeder = make_feeder()

    assert feeder.code == "HT-IN-01"
    assert feeder.feeder_type is HTFeederType.INCOMER
    assert feeder.switching_device is HTSwitchingDevice.VCB
    assert feeder.rated_normal_current_a == Decimal("630")


@pytest.mark.unit
def test_ht_feeder_text_is_trimmed() -> None:
    feeder = HTFeederInput(
        code="  HT-FDR-01  ",
        name="  Transformer Feeder  ",
        feeder_type=HTFeederType.TRANSFORMER_FEEDER,
        switching_device=HTSwitchingDevice.VCB,
        design_current_a=Decimal("200"),
        prospective_short_circuit_current_ka=Decimal("20"),
        rated_normal_current_a=Decimal("630"),
        rated_short_circuit_breaking_current_ka=Decimal("25"),
        rated_short_time_withstand_current_ka=Decimal("25"),
        short_time_withstand_duration_s=Decimal("3"),
        rated_peak_withstand_current_ka=Decimal("63"),
        ct_primary_current_a=Decimal("300"),
        notes="  Approved feeder  ",
    )

    assert feeder.code == "HT-FDR-01"
    assert feeder.name == "Transformer Feeder"
    assert feeder.notes == "Approved feeder"


@pytest.mark.unit
def test_feeder_rating_below_design_current_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="rated_normal_current_a must not be below",
    ):
        HTFeederInput(
            code="BAD-01",
            name="Invalid Feeder",
            feeder_type=HTFeederType.INCOMER,
            switching_device=HTSwitchingDevice.VCB,
            design_current_a=Decimal("800"),
            prospective_short_circuit_current_ka=Decimal("20"),
            rated_normal_current_a=Decimal("630"),
            rated_short_circuit_breaking_current_ka=Decimal("25"),
            rated_short_time_withstand_current_ka=Decimal("25"),
            short_time_withstand_duration_s=Decimal("3"),
            rated_peak_withstand_current_ka=Decimal("63"),
            ct_primary_current_a=Decimal("1000"),
        )


@pytest.mark.unit
def test_breaking_capacity_below_fault_level_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="breaking current must not be below",
    ):
        HTFeederInput(
            code="BAD-02",
            name="Invalid Breaking Capacity",
            feeder_type=HTFeederType.INCOMER,
            switching_device=HTSwitchingDevice.VCB,
            design_current_a=Decimal("400"),
            prospective_short_circuit_current_ka=Decimal("31.5"),
            rated_normal_current_a=Decimal("630"),
            rated_short_circuit_breaking_current_ka=Decimal("25"),
            rated_short_time_withstand_current_ka=Decimal("31.5"),
            short_time_withstand_duration_s=Decimal("3"),
            rated_peak_withstand_current_ka=Decimal("80"),
            ct_primary_current_a=Decimal("600"),
        )


@pytest.mark.unit
def test_invalid_ct_secondary_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="ct_secondary_current_a must be 1 or 5",
    ):
        HTFeederInput(
            code="BAD-CT",
            name="Invalid CT",
            feeder_type=HTFeederType.INCOMER,
            switching_device=HTSwitchingDevice.VCB,
            design_current_a=Decimal("400"),
            prospective_short_circuit_current_ka=Decimal("20"),
            rated_normal_current_a=Decimal("630"),
            rated_short_circuit_breaking_current_ka=Decimal("25"),
            rated_short_time_withstand_current_ka=Decimal("25"),
            short_time_withstand_duration_s=Decimal("3"),
            rated_peak_withstand_current_ka=Decimal("63"),
            ct_primary_current_a=Decimal("600"),
            ct_secondary_current_a=Decimal("2"),
        )


@pytest.mark.unit
def test_duplicate_relay_functions_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="relay functions must be unique",
    ):
        HTFeederInput(
            code="BAD-RLY",
            name="Invalid Relay",
            feeder_type=HTFeederType.INCOMER,
            switching_device=HTSwitchingDevice.VCB,
            design_current_a=Decimal("400"),
            prospective_short_circuit_current_ka=Decimal("20"),
            rated_normal_current_a=Decimal("630"),
            rated_short_circuit_breaking_current_ka=Decimal("25"),
            rated_short_time_withstand_current_ka=Decimal("25"),
            short_time_withstand_duration_s=Decimal("3"),
            rated_peak_withstand_current_ka=Decimal("63"),
            ct_primary_current_a=Decimal("600"),
            relay_functions=(
                HTRelayFunction.OVERCURRENT,
                HTRelayFunction.OVERCURRENT,
            ),
        )


@pytest.mark.unit
def test_create_valid_ht_panel() -> None:
    panel = make_panel()

    assert panel.code == "HTP-001"
    assert panel.system_voltage is HTSystemVoltage.KV_11
    assert panel.busbar_rated_current_a == Decimal("1250")
    assert len(panel.feeders) == 1


@pytest.mark.unit
def test_duplicate_feeder_codes_are_rejected() -> None:
    first = make_feeder(code="FDR-01")
    second = make_feeder(code="FDR-01")

    with pytest.raises(
        ValueError,
        match="HT feeder codes must be unique",
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
            busbar_rated_current_a=Decimal("400"),
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
def test_valid_two_section_panel() -> None:
    panel = make_panel(
        bus_sections=2,
        bus_couplers=1,
    )

    assert panel.bus_sections == 2
    assert panel.bus_couplers == 1
