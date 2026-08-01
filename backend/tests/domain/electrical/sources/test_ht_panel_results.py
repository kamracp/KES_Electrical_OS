"""
Unit tests for HT panel engineering result models.
KESE-S2-M9
"""

from decimal import Decimal

import pytest

from app.domain.electrical.sources.ht_panel_models import (
    HTFeederType,
    HTPanelConstruction,
    HTPanelInstallation,
    HTRelayFunction,
    HTSwitchingDevice,
    HTSystemVoltage,
)
from app.domain.electrical.sources.ht_panel_results import (
    HTFeederResult,
    HTPanelSizingResult,
    HTPanelSizingStatus,
    HTPanelWarning,
    HTPanelWarningCode,
)


def make_warning() -> HTPanelWarning:
    return HTPanelWarning(
        code=HTPanelWarningCode.CT_RATIO_MARGIN_LOW,
        message="CT ratio margin is low.",
    )


def make_feeder_result(
    *,
    code: str = "HT-IN-01",
    warnings: tuple[HTPanelWarning, ...] = (),
) -> HTFeederResult:
    return HTFeederResult(
        code=code,
        name="Main HT Incomer",
        feeder_type=HTFeederType.INCOMER,
        switching_device=HTSwitchingDevice.VCB,
        design_current_a=Decimal("400"),
        rated_normal_current_a=Decimal("630"),
        current_loading_percent=Decimal("63.4921"),
        prospective_short_circuit_current_ka=Decimal("20"),
        rated_short_circuit_breaking_current_ka=Decimal("25"),
        breaking_capacity_margin_ka=Decimal("5"),
        rated_short_time_withstand_current_ka=Decimal("25"),
        short_time_withstand_margin_ka=Decimal("5"),
        short_time_withstand_duration_s=Decimal("3"),
        rated_peak_withstand_current_ka=Decimal("63"),
        ct_primary_current_a=Decimal("600"),
        ct_secondary_current_a=Decimal("1"),
        ct_ratio="600/1",
        ct_margin_a=Decimal("200"),
        relay_functions=(
            HTRelayFunction.OVERCURRENT,
            HTRelayFunction.EARTH_FAULT,
        ),
        warnings=warnings,
    )


def make_panel_result(
    **overrides: object,
) -> HTPanelSizingResult:
    feeder = make_feeder_result()

    values: dict[str, object] = {
        "code": "HTP-001",
        "name": "11 kV Main HT Panel",
        "system_voltage": HTSystemVoltage.KV_11,
        "installation": HTPanelInstallation.INDOOR,
        "construction": HTPanelConstruction.METAL_CLAD,
        "total_feeders": 1,
        "active_feeders": 1,
        "spare_feeders": 0,
        "bus_sections": 1,
        "bus_couplers": 0,
        "maximum_feeder_current_a": Decimal("630"),
        "aggregate_design_current_a": Decimal("400"),
        "busbar_rated_current_a": Decimal("1250"),
        "busbar_loading_percent": Decimal("32"),
        "busbar_spare_capacity_a": Decimal("850"),
        "maximum_fault_current_ka": Decimal("20"),
        "busbar_short_time_withstand_current_ka": Decimal("25"),
        "busbar_fault_margin_ka": Decimal("5"),
        "busbar_peak_withstand_current_ka": Decimal("63"),
        "feeder_results": (feeder,),
        "status": HTPanelSizingStatus.VALID,
        "warnings": (),
    }

    values.update(overrides)

    return HTPanelSizingResult(**values)


@pytest.mark.unit
def test_create_valid_ht_feeder_result() -> None:
    result = make_feeder_result()

    assert result.code == "HT-IN-01"
    assert result.ct_ratio == "600/1"
    assert result.breaking_capacity_margin_ka == Decimal("5")


@pytest.mark.unit
def test_feeder_result_text_is_trimmed() -> None:
    result = make_feeder_result(
        code="  HT-IN-01  ",
    )

    assert result.code == "HT-IN-01"


@pytest.mark.unit
def test_warning_message_is_trimmed() -> None:
    warning = HTPanelWarning(
        code=HTPanelWarningCode.CT_RATIO_MARGIN_LOW,
        message="  CT ratio margin is low.  ",
    )

    assert warning.message == "CT ratio margin is low."


@pytest.mark.unit
def test_invalid_warning_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="HTPanelWarningCode",
    ):
        HTPanelWarning(
            code="INVALID",  # type: ignore[arg-type]
            message="Invalid warning.",
        )


@pytest.mark.unit
def test_create_valid_ht_panel_result() -> None:
    result = make_panel_result()

    assert result.code == "HTP-001"
    assert result.total_feeders == 1
    assert result.status is HTPanelSizingStatus.VALID


@pytest.mark.unit
def test_total_feeders_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="total_feeders must equal",
    ):
        make_panel_result(
            total_feeders=2,
        )


@pytest.mark.unit
def test_feeder_result_count_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="feeder_results count must equal",
    ):
        make_panel_result(
            feeder_results=(),
        )


@pytest.mark.unit
def test_duplicate_panel_warning_codes_are_rejected() -> None:
    warning = make_warning()

    with pytest.raises(
        ValueError,
        match="panel warning codes must be unique",
    ):
        make_panel_result(
            status=HTPanelSizingStatus.WARNING,
            warnings=(warning, warning),
        )


@pytest.mark.unit
def test_invalid_feeder_warning_records_are_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="HTPanelWarning records",
    ):
        make_feeder_result(
            warnings=("invalid",),  # type: ignore[arg-type]
        )
