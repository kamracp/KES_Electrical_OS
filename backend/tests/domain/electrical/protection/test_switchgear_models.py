"""
Unit tests for intelligent switchgear selection models.
KESE-S2-M11
"""

from decimal import Decimal

import pytest

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


def make_candidate(
    **overrides: object,
) -> SwitchgearCandidate:
    values: dict[str, object] = {
        "code": "ACB-1600-65",
        "family": "Master Range",
        "manufacturer": ManufacturerSource.MANUFACTURER_NEUTRAL,
        "device_type": SwitchgearDeviceType.ACB,
        "trip_unit_type": SwitchgearTripUnitType.ELECTRONIC_LSIG,
        "frame_current_a": Decimal("1600"),
        "rated_current_a": Decimal("1600"),
        "rated_operational_voltage_v": Decimal("690"),
        "ultimate_breaking_capacity_ka": Decimal("65"),
        "service_breaking_capacity_ka": Decimal("65"),
        "short_time_withstand_current_ka": Decimal("65"),
        "service_breaking_ratio": Decimal("1"),
        "number_of_poles": 4,
        "withdrawable": True,
        "communication_capable": True,
        "reference_document": "Manufacturer catalogue",
        "reference_revision": "2026",
    }

    values.update(overrides)

    return SwitchgearCandidate(**values)


def make_selection(
    **overrides: object,
) -> SwitchgearSelectionInput:
    values: dict[str, object] = {
        "code": "SEL-001",
        "name": "Main PCC Incomer",
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
            short_time_pickup_a=Decimal("6000"),
            instantaneous_pickup_a=Decimal("12000"),
            ground_fault_pickup_a=Decimal("400"),
        ),
        "candidates": (
            make_candidate(),
        ),
        "cpwd_reference": "CPWD General Specifications",
        "standard_reference": "IEC 60947-2",
        "manufacturer_reference_required": False,
    }

    values.update(overrides)

    return SwitchgearSelectionInput(**values)


@pytest.mark.unit
def test_create_valid_switchgear_candidate() -> None:
    candidate = make_candidate()

    assert candidate.code == "ACB-1600-65"
    assert candidate.device_type is SwitchgearDeviceType.ACB
    assert candidate.service_breaking_ratio == Decimal("1")


@pytest.mark.unit
def test_candidate_text_is_trimmed() -> None:
    candidate = make_candidate(
        code="  ACB-1600-65  ",
        family="  Master Range  ",
        notes="  Approved  ",
    )

    assert candidate.code == "ACB-1600-65"
    assert candidate.family == "Master Range"
    assert candidate.notes == "Approved"


@pytest.mark.unit
def test_rated_current_above_frame_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must not exceed frame_current_a",
    ):
        make_candidate(
            frame_current_a=Decimal("1600"),
            rated_current_a=Decimal("2000"),
        )


@pytest.mark.unit
def test_ics_above_icu_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="service breaking capacity must not exceed",
    ):
        make_candidate(
            ultimate_breaking_capacity_ka=Decimal("50"),
            service_breaking_capacity_ka=Decimal("65"),
        )


@pytest.mark.unit
def test_invalid_service_breaking_ratio_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must equal Ics divided by Icu",
    ):
        make_candidate(
            ultimate_breaking_capacity_ka=Decimal("65"),
            service_breaking_capacity_ka=Decimal("50"),
            service_breaking_ratio=Decimal("1"),
        )


@pytest.mark.unit
def test_create_valid_selection_input() -> None:
    selection = make_selection()

    assert selection.code == "SEL-001"
    assert selection.application is SwitchgearApplication.INCOMER
    assert len(selection.candidates) == 1


@pytest.mark.unit
def test_empty_candidates_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="at least one switchgear candidate",
    ):
        make_selection(
            candidates=(),
        )


@pytest.mark.unit
def test_duplicate_candidate_codes_are_rejected() -> None:
    candidate = make_candidate()

    with pytest.raises(
        ValueError,
        match="candidate codes must be unique",
    ):
        make_selection(
            candidates=(candidate, candidate),
        )


@pytest.mark.unit
def test_coordination_requires_device_reference() -> None:
    with pytest.raises(
        ValueError,
        match="coordination selection requires",
    ):
        make_selection(
            coordination_type=CoordinationType.SELECTIVITY,
            upstream_device_code=None,
            downstream_device_code=None,
        )


@pytest.mark.unit
def test_valid_coordination_reference() -> None:
    selection = make_selection(
        coordination_type=CoordinationType.TYPE_2,
        upstream_device_code="ACB-UP-01",
    )

    assert selection.coordination_type is CoordinationType.TYPE_2
    assert selection.upstream_device_code == "ACB-UP-01"


@pytest.mark.unit
def test_negative_short_time_requirement_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must not be negative",
    ):
        make_selection(
            minimum_short_time_withstand_current_ka=Decimal("-1"),
        )
