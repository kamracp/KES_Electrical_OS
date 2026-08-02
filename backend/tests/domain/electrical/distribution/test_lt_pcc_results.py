"""
Unit tests for LT PCC / Main Panel result models.
KESE-S2-M10
"""

from decimal import Decimal

import pytest

from app.domain.electrical.distribution.lt_pcc_models import (
    LTFeederType,
    LTPanelFormOfSeparation,
    LTPanelInstallation,
    LTSystemVoltage,
    LTSwitchingDevice,
    LTTripUnitType,
)
from app.domain.electrical.distribution.lt_pcc_results import (
    LTFeederResult,
    LTPCCSizingResult,
    LTPCCSizingStatus,
    LTPCCWarning,
    LTPCCWarningCode,
)


def make_warning() -> LTPCCWarning:
    return LTPCCWarning(
        code=LTPCCWarningCode.ICU_MARGIN_LOW,
        message="Icu margin is low.",
    )


def make_feeder_result(
    *,
    code: str = "TR-IN-01",
    warnings: tuple[LTPCCWarning, ...] = (),
) -> LTFeederResult:
    return LTFeederResult(
        code=code,
        name="Transformer Incomer",
        feeder_type=LTFeederType.TRANSFORMER_INCOMER,
        switching_device=LTSwitchingDevice.ACB,
        trip_unit_type=LTTripUnitType.ELECTRONIC_LSIG,
        design_current_a=Decimal("1400"),
        rated_current_a=Decimal("1600"),
        loading_percent=Decimal("87.5000"),
        spare_current_capacity_a=Decimal("200"),
        prospective_short_circuit_current_ka=Decimal("50"),
        rated_ultimate_breaking_capacity_ka=Decimal("65"),
        icu_margin_ka=Decimal("15"),
        rated_service_breaking_capacity_ka=Decimal("65"),
        ics_margin_ka=Decimal("15"),
        rated_short_time_withstand_current_ka=Decimal("65"),
        icw_margin_ka=Decimal("15"),
        number_of_poles=4,
        cable_count=4,
        spare_feeder=False,
        warnings=warnings,
    )


def make_panel_result(
    **overrides: object,
) -> LTPCCSizingResult:
    feeder = make_feeder_result()

    values: dict[str, object] = {
        "code": "PCC-001",
        "name": "Main LT PCC",
        "system_voltage": LTSystemVoltage.V_415,
        "installation": LTPanelInstallation.INDOOR,
        "form_of_separation": LTPanelFormOfSeparation.FORM_4B,
        "total_feeders": 1,
        "active_feeders": 1,
        "spare_feeders": 0,
        "bus_sections": 1,
        "bus_couplers": 0,
        "aggregate_design_current_a": Decimal("1400"),
        "maximum_feeder_rated_current_a": Decimal("1600"),
        "busbar_rated_current_a": Decimal("2500"),
        "busbar_loading_percent": Decimal("56.0000"),
        "busbar_spare_capacity_a": Decimal("1100"),
        "maximum_fault_current_ka": Decimal("50"),
        "busbar_short_time_withstand_current_ka": Decimal("65"),
        "busbar_fault_margin_ka": Decimal("15"),
        "busbar_peak_withstand_current_ka": Decimal("143"),
        "neutral_bus_rating_percent": Decimal("100"),
        "earth_bus_rating_percent": Decimal("50"),
        "apfc_required": True,
        "metering_required": True,
        "remote_operation_required": False,
        "feeder_results": (feeder,),
        "status": LTPCCSizingStatus.VALID,
        "warnings": (),
    }

    values.update(overrides)

    return LTPCCSizingResult(**values)


@pytest.mark.unit
def test_create_valid_lt_feeder_result() -> None:
    result = make_feeder_result()

    assert result.code == "TR-IN-01"
    assert result.loading_percent == Decimal("87.5000")
    assert result.icu_margin_ka == Decimal("15")


@pytest.mark.unit
def test_feeder_result_text_is_trimmed() -> None:
    result = make_feeder_result(
        code="  TR-IN-01  ",
    )

    assert result.code == "TR-IN-01"


@pytest.mark.unit
def test_warning_message_is_trimmed() -> None:
    warning = LTPCCWarning(
        code=LTPCCWarningCode.ICU_MARGIN_LOW,
        message="  Icu margin is low.  ",
    )

    assert warning.message == "Icu margin is low."


@pytest.mark.unit
def test_invalid_warning_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="LTPCCWarningCode",
    ):
        LTPCCWarning(
            code="INVALID",  # type: ignore[arg-type]
            message="Invalid warning.",
        )


@pytest.mark.unit
def test_duplicate_feeder_warning_codes_are_rejected() -> None:
    warning = make_warning()

    with pytest.raises(
        ValueError,
        match="feeder warning codes must be unique",
    ):
        make_feeder_result(
            warnings=(warning, warning),
        )


@pytest.mark.unit
def test_create_valid_lt_pcc_result() -> None:
    result = make_panel_result()

    assert result.code == "PCC-001"
    assert result.total_feeders == 1
    assert result.status is LTPCCSizingStatus.VALID


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
def test_invalid_feeder_result_records_are_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="LTFeederResult records",
    ):
        make_panel_result(
            feeder_results=("invalid",),  # type: ignore[arg-type]
        )


@pytest.mark.unit
def test_duplicate_panel_warning_codes_are_rejected() -> None:
    warning = make_warning()

    with pytest.raises(
        ValueError,
        match="panel warning codes must be unique",
    ):
        make_panel_result(
            status=LTPCCSizingStatus.WARNING,
            warnings=(warning, warning),
        )


@pytest.mark.unit
def test_invalid_panel_status_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="LTPCCSizingStatus",
    ):
        make_panel_result(
            status="INVALID",  # type: ignore[arg-type]
        )
