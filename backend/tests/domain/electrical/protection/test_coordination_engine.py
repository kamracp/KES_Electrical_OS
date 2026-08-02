"""
Unit tests for protection coordination engine.
KESE-S2-M11 Phase-2
"""

from decimal import Decimal

import pytest

from app.domain.electrical.protection.coordination_engine import (
    calculate_coordination_study,
)
from app.domain.electrical.protection.coordination_models import (
    CoordinationCatalogueEntry,
    CoordinationDeviceReference,
    CoordinationObjective,
    CoordinationStudyInput,
    CoordinationVerificationStatus,
    StarterMethod,
)
from app.domain.electrical.protection.coordination_results import (
    CoordinationStudyStatus,
    CoordinationWarningCode,
)


def make_device(
    code: str,
) -> CoordinationDeviceReference:
    return CoordinationDeviceReference(
        code=code,
        family="Master Range",
        manufacturer="Schneider Electric",
        device_type="ACB",
        rated_current_a=Decimal("1600"),
        breaking_capacity_ka=Decimal("65"),
    )


def make_selectivity_entry(
    *,
    code: str = "SEL-001",
    limit_ka: Decimal = Decimal("35"),
    verification_status: CoordinationVerificationStatus = (
        CoordinationVerificationStatus.VERIFIED
    ),
    upstream_code: str = "ACB-UP-01",
    downstream_code: str = "MCCB-DN-01",
) -> CoordinationCatalogueEntry:
    return CoordinationCatalogueEntry(
        code=code,
        objective=CoordinationObjective.SELECTIVITY,
        verification_status=verification_status,
        upstream_device=make_device(upstream_code),
        downstream_device=make_device(downstream_code),
        maximum_selective_current_ka=limit_ka,
        manufacturer_document=(
            "Selectivity Table"
            if verification_status
            is CoordinationVerificationStatus.VERIFIED
            else None
        ),
    )


def make_type_2_entry(
    *,
    motor_power_kw: Decimal = Decimal("45"),
    starter_method: StarterMethod = StarterMethod.DOL,
) -> CoordinationCatalogueEntry:
    return CoordinationCatalogueEntry(
        code="T2-001",
        objective=CoordinationObjective.TYPE_2,
        verification_status=(
            CoordinationVerificationStatus.VERIFIED
        ),
        upstream_device=make_device("MCCB-UP-01"),
        downstream_device=make_device("MPCB-DN-01"),
        starter_method=starter_method,
        motor_power_kw=motor_power_kw,
        manufacturer_document="Type-2 Coordination Table",
    )


def make_selectivity_study(
    **overrides: object,
) -> CoordinationStudyInput:
    values: dict[str, object] = {
        "code": "STUDY-001",
        "name": "Main PCC Selectivity Study",
        "objective": CoordinationObjective.SELECTIVITY,
        "prospective_fault_current_ka": Decimal("30"),
        "upstream_device": make_device("ACB-UP-01"),
        "downstream_device": make_device("MCCB-DN-01"),
        "catalogue_entries": (
            make_selectivity_entry(),
        ),
        "require_verified_entry": True,
    }

    values.update(overrides)

    return CoordinationStudyInput(**values)


@pytest.mark.unit
def test_verified_selectivity_match() -> None:
    result = calculate_coordination_study(
        make_selectivity_study()
    )

    assert result.status is CoordinationStudyStatus.VERIFIED
    assert result.coordination_verified is True
    assert result.selected_entry_code == "SEL-001"
    assert result.selected_limit_ka == Decimal("35.0000")
    assert result.fault_level_margin_ka == Decimal("5.0000")


@pytest.mark.unit
def test_fault_level_exceeding_limit_returns_no_match() -> None:
    result = calculate_coordination_study(
        make_selectivity_study(
            prospective_fault_current_ka=Decimal("40"),
        )
    )

    assert result.status is CoordinationStudyStatus.NO_MATCH
    assert result.coordination_verified is False

    assert any(
        warning.code is CoordinationWarningCode.NO_MATCHING_ENTRY
        for warning in result.warnings
    )


@pytest.mark.unit
def test_device_pair_mismatch_returns_no_match() -> None:
    result = calculate_coordination_study(
        make_selectivity_study(
            catalogue_entries=(
                make_selectivity_entry(
                    downstream_code="MCCB-OTHER",
                ),
            ),
        )
    )

    assert result.status is CoordinationStudyStatus.NO_MATCH

    evaluation = result.entry_evaluations[0]

    assert evaluation.device_pair_match is False

    assert any(
        warning.code
        is CoordinationWarningCode.DEVICE_PAIR_MISMATCH
        for warning in evaluation.warnings
    )


@pytest.mark.unit
def test_unverified_entry_rejected_when_verification_required() -> None:
    result = calculate_coordination_study(
        make_selectivity_study(
            catalogue_entries=(
                make_selectivity_entry(
                    verification_status=(
                        CoordinationVerificationStatus.UNVERIFIED
                    ),
                ),
            ),
            require_verified_entry=True,
        )
    )

    assert result.status is CoordinationStudyStatus.NO_MATCH


@pytest.mark.unit
def test_unverified_entry_allowed_with_warning() -> None:
    result = calculate_coordination_study(
        make_selectivity_study(
            catalogue_entries=(
                make_selectivity_entry(
                    verification_status=(
                        CoordinationVerificationStatus.UNVERIFIED
                    ),
                ),
            ),
            require_verified_entry=False,
        )
    )

    assert result.status is CoordinationStudyStatus.WARNING
    assert result.coordination_verified is False

    assert any(
        warning.code is CoordinationWarningCode.UNVERIFIED_ENTRY
        for warning in result.warnings
    )


@pytest.mark.unit
def test_best_matching_entry_is_selected() -> None:
    result = calculate_coordination_study(
        make_selectivity_study(
            catalogue_entries=(
                make_selectivity_entry(
                    code="SEL-050",
                    limit_ka=Decimal("50"),
                ),
                make_selectivity_entry(
                    code="SEL-035",
                    limit_ka=Decimal("35"),
                ),
            ),
        )
    )

    assert result.matching_entries == 2
    assert result.selected_entry_code == "SEL-035"
    assert result.fault_level_margin_ka == Decimal("5.0000")


@pytest.mark.unit
def test_verified_type_2_coordination_match() -> None:
    study = CoordinationStudyInput(
        code="STUDY-T2",
        name="Motor Type-2 Coordination Study",
        objective=CoordinationObjective.TYPE_2,
        prospective_fault_current_ka=Decimal("30"),
        upstream_device=make_device("MCCB-UP-01"),
        downstream_device=make_device("MPCB-DN-01"),
        catalogue_entries=(
            make_type_2_entry(),
        ),
        required_motor_power_kw=Decimal("45"),
        required_starter_method=StarterMethod.DOL,
        require_verified_entry=True,
    )

    result = calculate_coordination_study(study)

    assert result.status is CoordinationStudyStatus.VERIFIED
    assert result.selected_starter_method is StarterMethod.DOL
    assert result.selected_motor_power_kw == Decimal("45")


@pytest.mark.unit
def test_type_2_motor_power_mismatch() -> None:
    study = CoordinationStudyInput(
        code="STUDY-T2-BAD",
        name="Motor Type-2 Coordination Study",
        objective=CoordinationObjective.TYPE_2,
        prospective_fault_current_ka=Decimal("30"),
        upstream_device=make_device("MCCB-UP-01"),
        downstream_device=make_device("MPCB-DN-01"),
        catalogue_entries=(
            make_type_2_entry(
                motor_power_kw=Decimal("30"),
            ),
        ),
        required_motor_power_kw=Decimal("45"),
        required_starter_method=StarterMethod.DOL,
    )

    result = calculate_coordination_study(study)

    assert result.status is CoordinationStudyStatus.NO_MATCH

    evaluation = result.entry_evaluations[0]

    assert any(
        warning.code
        is CoordinationWarningCode.MOTOR_POWER_MISMATCH
        for warning in evaluation.warnings
    )


@pytest.mark.unit
def test_invalid_input_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="CoordinationStudyInput record",
    ):
        calculate_coordination_study(
            "invalid"  # type: ignore[arg-type]
        )