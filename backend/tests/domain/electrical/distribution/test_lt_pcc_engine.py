"""
Unit tests for LT PCC / Main Panel engineering engine.
KESE-S2-M10
"""

from decimal import Decimal

import pytest

from app.domain.electrical.distribution.lt_pcc_engine import (
    calculate_lt_pcc_sizing,
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
        "spare_feeders": 0,
        "ip_rating": "IP42",
        "apfc_required": False,
        "metering_required": True,
        "remote_operation_required": False,
    }

    values.update(overrides)

    return LTPCCSizingInput(**values)


@pytest.mark.unit
def test_calculate_lt_pcc_sizing() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel()
    )

    assert result.code == "PCC-001"
    assert result.total_feeders == 1
    assert result.active_feeders == 1
    assert result.spare_feeders == 0
    assert result.aggregate_design_current_a == Decimal("1400.0000")
    assert result.busbar_loading_percent == Decimal("56.0000")
    assert result.busbar_spare_capacity_a == Decimal("1100.0000")
    assert result.maximum_fault_current_ka == Decimal("50.0000")


@pytest.mark.unit
def test_lt_feeder_engineering_result() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel()
    )

    feeder = result.feeder_results[0]

    assert feeder.loading_percent == Decimal("87.5000")
    assert feeder.spare_current_capacity_a == Decimal("200.0000")
    assert feeder.icu_margin_ka == Decimal("15.0000")
    assert feeder.ics_margin_ka == Decimal("15.0000")
    assert feeder.icw_margin_ka == Decimal("15.0000")


@pytest.mark.unit
def test_low_icu_margin_warning() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel(
            feeders=(
                make_feeder(
                    rated_ultimate_breaking_capacity_ka=(
                        Decimal("60")
                    ),
                    rated_service_breaking_capacity_ka=(
                        Decimal("60")
                    ),
                ),
            ),
        )
    )

    assert result.status is LTPCCSizingStatus.WARNING

    assert any(
        warning.code is LTPCCWarningCode.ICU_MARGIN_LOW
        for warning in result.feeder_results[0].warnings
    )


@pytest.mark.unit
def test_low_ics_margin_warning() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel(
            feeders=(
                make_feeder(
                    rated_service_breaking_capacity_ka=(
                        Decimal("60")
                    ),
                ),
            ),
        )
    )

    assert any(
        warning.code is LTPCCWarningCode.ICS_MARGIN_LOW
        for warning in result.feeder_results[0].warnings
    )


@pytest.mark.unit
def test_low_icw_margin_warning() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel(
            feeders=(
                make_feeder(
                    rated_short_time_withstand_current_ka=(
                        Decimal("60")
                    ),
                ),
            ),
        )
    )

    assert any(
        warning.code is LTPCCWarningCode.ICW_MARGIN_LOW
        for warning in result.feeder_results[0].warnings
    )


@pytest.mark.unit
def test_low_feeder_spare_capacity_warning() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel(
            feeders=(
                make_feeder(
                    design_current_a=Decimal("1550"),
                ),
            ),
        )
    )

    assert any(
        warning.code
        is LTPCCWarningCode.LOW_FEEDER_SPARE_CAPACITY
        for warning in result.feeder_results[0].warnings
    )


@pytest.mark.unit
def test_high_busbar_loading_warning() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel(
            busbar_rated_current_a=Decimal("1600"),
            feeders=(
                make_feeder(
                    design_current_a=Decimal("1500"),
                ),
            ),
        )
    )

    assert any(
        warning.code
        is LTPCCWarningCode.HIGH_BUSBAR_LOADING
        for warning in result.warnings
    )


@pytest.mark.unit
def test_low_busbar_loading_warning() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel(
            busbar_rated_current_a=Decimal("6300"),
        )
    )

    assert any(
        warning.code
        is LTPCCWarningCode.LOW_BUSBAR_LOADING
        for warning in result.warnings
    )


@pytest.mark.unit
def test_apfc_review_warning() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel(
            apfc_required=True,
        )
    )

    assert any(
        warning.code
        is LTPCCWarningCode.APFC_REVIEW_REQUIRED
        for warning in result.warnings
    )


@pytest.mark.unit
def test_outdoor_remote_operation_warning() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel(
            installation=LTPanelInstallation.OUTDOOR,
            remote_operation_required=False,
        )
    )

    assert any(
        warning.code
        is LTPCCWarningCode.REMOTE_OPERATION_RECOMMENDED
        for warning in result.warnings
    )


@pytest.mark.unit
def test_spare_feeder_result_is_created() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel(
            spare_feeders=2,
        )
    )

    assert result.total_feeders == 3
    assert result.active_feeders == 1
    assert result.spare_feeders == 2
    assert result.feeder_results[1].code == "PCC-001-SPARE-01"
    assert result.feeder_results[2].code == "PCC-001-SPARE-02"


@pytest.mark.unit
def test_multiple_active_feeders_are_aggregated() -> None:
    result = calculate_lt_pcc_sizing(
        make_panel(
            feeders=(
                make_feeder(
                    code="TR-IN-01",
                    design_current_a=Decimal("1000"),
                ),
                make_feeder(
                    code="DG-IN-01",
                    feeder_type=LTFeederType.DG_INCOMER,
                    design_current_a=Decimal("600"),
                    rated_current_a=Decimal("800"),
                ),
            ),
        )
    )

    assert result.active_feeders == 2
    assert result.aggregate_design_current_a == Decimal("1600.0000")


@pytest.mark.unit
def test_invalid_engine_input_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="LTPCCSizingInput record",
    ):
        calculate_lt_pcc_sizing(
            "invalid"  # type: ignore[arg-type]
        )
