"""
Unit tests for HT panel engineering engine.
KESE-S2-M9
"""

from decimal import Decimal

import pytest

from app.domain.electrical.sources.ht_panel_engine import (
    calculate_ht_panel_sizing,
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


def make_feeder(
    **overrides: object,
) -> HTFeederInput:
    values: dict[str, object] = {
        "code": "HT-IN-01",
        "name": "Main HT Incomer",
        "feeder_type": HTFeederType.INCOMER,
        "switching_device": HTSwitchingDevice.VCB,
        "design_current_a": Decimal("400"),
        "prospective_short_circuit_current_ka": Decimal("20"),
        "rated_normal_current_a": Decimal("630"),
        "rated_short_circuit_breaking_current_ka": Decimal("25"),
        "rated_short_time_withstand_current_ka": Decimal("25"),
        "short_time_withstand_duration_s": Decimal("3"),
        "rated_peak_withstand_current_ka": Decimal("63"),
        "ct_primary_current_a": Decimal("600"),
        "ct_secondary_current_a": Decimal("1"),
        "relay_functions": (
            HTRelayFunction.OVERCURRENT,
            HTRelayFunction.EARTH_FAULT,
        ),
    }

    values.update(overrides)

    return HTFeederInput(**values)


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
        "spare_feeders": 0,
        "arc_classification_required": False,
        "remote_operation_required": False,
    }

    values.update(overrides)

    return HTPanelSizingInput(**values)


@pytest.mark.unit
def test_calculate_ht_panel_sizing() -> None:
    result = calculate_ht_panel_sizing(
        make_panel()
    )

    assert result.code == "HTP-001"
    assert result.total_feeders == 1
    assert result.active_feeders == 1
    assert result.spare_feeders == 0
    assert result.aggregate_design_current_a == Decimal("400.0000")
    assert result.busbar_loading_percent == Decimal("32.0000")
    assert result.busbar_spare_capacity_a == Decimal("850.0000")
    assert result.maximum_fault_current_ka == Decimal("20.0000")


@pytest.mark.unit
def test_feeder_engineering_result() -> None:
    result = calculate_ht_panel_sizing(
        make_panel()
    )

    feeder = result.feeder_results[0]

    assert feeder.current_loading_percent == Decimal("63.4921")
    assert feeder.breaking_capacity_margin_ka == Decimal("5.0000")
    assert feeder.short_time_withstand_margin_ka == Decimal("5.0000")
    assert feeder.ct_ratio == "6E+2/1"
    assert feeder.ct_margin_a == Decimal("200.0000")


@pytest.mark.unit
def test_low_breaking_capacity_margin_warning() -> None:
    result = calculate_ht_panel_sizing(
        make_panel(
            feeders=(
                make_feeder(
                    rated_short_circuit_breaking_current_ka=(
                        Decimal("24")
                    ),
                ),
            ),
        )
    )

    assert result.status is HTPanelSizingStatus.WARNING

    feeder_warnings = result.feeder_results[0].warnings

    assert any(
        warning.code
        is HTPanelWarningCode.BREAKING_CAPACITY_MARGIN_LOW
        for warning in feeder_warnings
    )


@pytest.mark.unit
def test_low_ct_margin_warning() -> None:
    result = calculate_ht_panel_sizing(
        make_panel(
            feeders=(
                make_feeder(
                    ct_primary_current_a=Decimal("450"),
                ),
            ),
        )
    )

    assert any(
        warning.code
        is HTPanelWarningCode.CT_RATIO_MARGIN_LOW
        for warning in result.feeder_results[0].warnings
    )


@pytest.mark.unit
def test_high_busbar_loading_warning() -> None:
    result = calculate_ht_panel_sizing(
        make_panel(
            busbar_rated_current_a=Decimal("630"),
            feeders=(
                make_feeder(
                    design_current_a=Decimal("600"),
                    rated_normal_current_a=Decimal("630"),
                    ct_primary_current_a=Decimal("800"),
                ),
            ),
        )
    )

    assert result.status is HTPanelSizingStatus.WARNING

    assert any(
        warning.code
        is HTPanelWarningCode.HIGH_BUSBAR_LOADING
        for warning in result.warnings
    )


@pytest.mark.unit
def test_low_busbar_loading_warning() -> None:
    result = calculate_ht_panel_sizing(
        make_panel(
            busbar_rated_current_a=Decimal("2000"),
        )
    )

    assert any(
        warning.code
        is HTPanelWarningCode.LOW_BUSBAR_LOADING
        for warning in result.warnings
    )


@pytest.mark.unit
def test_arc_classification_warning() -> None:
    result = calculate_ht_panel_sizing(
        make_panel(
            arc_classification_required=True,
        )
    )

    assert any(
        warning.code
        is HTPanelWarningCode.ARC_CLASSIFICATION_REQUIRED
        for warning in result.warnings
    )


@pytest.mark.unit
def test_outdoor_remote_operation_warning() -> None:
    result = calculate_ht_panel_sizing(
        make_panel(
            installation=HTPanelInstallation.OUTDOOR,
            remote_operation_required=False,
        )
    )

    assert any(
        warning.code
        is HTPanelWarningCode.REMOTE_OPERATION_RECOMMENDED
        for warning in result.warnings
    )


@pytest.mark.unit
def test_spare_feeder_compartment_is_created() -> None:
    result = calculate_ht_panel_sizing(
        make_panel(
            spare_feeders=2,
        )
    )

    assert result.total_feeders == 3
    assert result.active_feeders == 1
    assert result.spare_feeders == 2
    assert result.feeder_results[1].code == "HTP-001-SPARE-01"
    assert result.feeder_results[2].code == "HTP-001-SPARE-02"


@pytest.mark.unit
def test_multiple_active_feeders_are_aggregated() -> None:
    result = calculate_ht_panel_sizing(
        make_panel(
            feeders=(
                make_feeder(
                    code="HT-IN-01",
                    design_current_a=Decimal("300"),
                ),
                make_feeder(
                    code="HT-TR-01",
                    feeder_type=HTFeederType.TRANSFORMER_FEEDER,
                    design_current_a=Decimal("250"),
                    ct_primary_current_a=Decimal("400"),
                ),
            ),
        )
    )

    assert result.active_feeders == 2
    assert result.aggregate_design_current_a == Decimal("550.0000")


@pytest.mark.unit
def test_invalid_engine_input_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="HTPanelSizingInput record",
    ):
        calculate_ht_panel_sizing(
            "invalid"  # type: ignore[arg-type]
        )
