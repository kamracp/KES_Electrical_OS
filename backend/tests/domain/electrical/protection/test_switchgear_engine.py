"""
Unit tests for intelligent switchgear selection engine.
KESE-S2-M11
"""

from decimal import Decimal

import pytest

from app.domain.electrical.protection.switchgear_engine import (
    calculate_switchgear_selection,
)
from app.domain.electrical.protection.switchgear_models import (
    CoordinationType,
    ManufacturerSource,
    ProtectionSettingsInput,
    SwitchgearApplication,
    SwitchgearCandidate,
    SwitchgearDeviceType,
    SwitchgearSelectionInput,
    SwitchgearTripUnitType,
)
from app.domain.electrical.protection.switchgear_results import (
    SwitchgearSelectionStatus,
    SwitchgearWarningCode,
)


def make_candidate(**overrides):
    values = {
        "code": "ACB-1600-65",
        "family": "Master",
        "manufacturer": ManufacturerSource.MANUFACTURER_NEUTRAL,
        "device_type": SwitchgearDeviceType.ACB,
        "trip_unit_type": SwitchgearTripUnitType.ELECTRONIC_LSIG,
        "frame_current_a": Decimal("2000"),
        "rated_current_a": Decimal("2000"),
        "rated_operational_voltage_v": Decimal("690"),
        "ultimate_breaking_capacity_ka": Decimal("65"),
        "service_breaking_capacity_ka": Decimal("65"),
        "short_time_withstand_current_ka": Decimal("65"),
        "service_breaking_ratio": Decimal("1"),
        "number_of_poles": 4,
    }
    values.update(overrides)
    return SwitchgearCandidate(**values)


def make_input(**overrides):
    values = {
        "code": "SEL-001",
        "name": "Main PCC",
        "application": SwitchgearApplication.INCOMER,
        "required_device_type": SwitchgearDeviceType.ACB,
        "system_voltage_v": Decimal("415"),
        "design_current_a": Decimal("1400"),
        "prospective_short_circuit_current_ka": Decimal("50"),
        "minimum_service_breaking_ratio": Decimal("1"),
        "minimum_short_time_withstand_current_ka": Decimal("50"),
        "number_of_poles": 4,
        "coordination_type": CoordinationType.NONE,
        "protection_settings": ProtectionSettingsInput(
            long_time_pickup_a=Decimal("1400"),
        ),
        "candidates": (make_candidate(),),
    }
    values.update(overrides)
    return SwitchgearSelectionInput(**values)


@pytest.mark.unit
def test_select_candidate():
    result = calculate_switchgear_selection(make_input())

    assert result.status is SwitchgearSelectionStatus.SELECTED
    assert result.selected_candidate_code == "ACB-1600-65"


@pytest.mark.unit
def test_no_candidate_available():
    bad = make_candidate(
        rated_current_a=Decimal("800"),
        frame_current_a=Decimal("800"),
    )

    result = calculate_switchgear_selection(
        make_input(candidates=(bad,))
    )

    assert result.status is SwitchgearSelectionStatus.NO_SOLUTION

    assert any(
        warning.code is SwitchgearWarningCode.NO_SUITABLE_DEVICE
        for warning in result.warnings
    )


@pytest.mark.unit
def test_coordination_warning():
    result = calculate_switchgear_selection(
        make_input(
            coordination_type=CoordinationType.SELECTIVITY,
            upstream_device_code="UP-01",
        )
    )

    assert result.status is SwitchgearSelectionStatus.WARNING

    assert any(
        warning.code
        is SwitchgearWarningCode.COORDINATION_NOT_VERIFIED
        for warning in result.warnings
    )


@pytest.mark.unit
def test_manufacturer_reference_warning():
    result = calculate_switchgear_selection(
        make_input(
            manufacturer_reference_required=True,
        )
    )

    assert any(
        warning.code
        is SwitchgearWarningCode.MANUFACTURER_REFERENCE_REQUIRED
        for warning in result.warnings
    )


@pytest.mark.unit
def test_invalid_input_type():
    with pytest.raises(TypeError):
        calculate_switchgear_selection(
            "invalid"  # type: ignore[arg-type]
        )
