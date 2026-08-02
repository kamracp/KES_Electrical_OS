"""
Unit tests for protection coordination result models.
KESE-S2-M11 Phase-2
"""

from decimal import Decimal

import pytest

from app.domain.electrical.protection.coordination_models import (
    CoordinationObjective,
    CoordinationVerificationStatus,
    StarterMethod,
)
from app.domain.electrical.protection.coordination_results import (
    CoordinationEntryEvaluation,
    CoordinationStudyResult,
    CoordinationStudyStatus,
    CoordinationWarning,
    CoordinationWarningCode,
)


def make_warning() -> CoordinationWarning:
    return CoordinationWarning(
        code=CoordinationWarningCode.UNVERIFIED_ENTRY,
        message="Catalogue entry is not verified.",
    )


def make_evaluation(
    **overrides: object,
) -> CoordinationEntryEvaluation:
    values: dict[str, object] = {
        "entry_code": "SEL-001",
        "objective": CoordinationObjective.SELECTIVITY,
        "verification_status": (
            CoordinationVerificationStatus.VERIFIED
        ),
        "device_pair_match": True,
        "fault_level_adequate": True,
        "starter_method_match": True,
        "motor_power_adequate": True,
        "overall_match": True,
        "applicable_limit_ka": Decimal("35"),
        "fault_level_margin_ka": Decimal("5"),
        "starter_method": None,
        "motor_power_kw": None,
        "warnings": (),
    }

    values.update(overrides)

    return CoordinationEntryEvaluation(**values)


def make_result(
    **overrides: object,
) -> CoordinationStudyResult:
    evaluation = make_evaluation()

    values: dict[str, object] = {
        "code": "STUDY-001",
        "name": "Main PCC Selectivity Study",
        "objective": CoordinationObjective.SELECTIVITY,
        "prospective_fault_current_ka": Decimal("30"),
        "evaluated_entries": 1,
        "matching_entries": 1,
        "selected_entry_code": "SEL-001",
        "selected_verification_status": (
            CoordinationVerificationStatus.VERIFIED
        ),
        "selected_limit_ka": Decimal("35"),
        "fault_level_margin_ka": Decimal("5"),
        "selected_starter_method": None,
        "selected_motor_power_kw": None,
        "coordination_verified": True,
        "entry_evaluations": (evaluation,),
        "status": CoordinationStudyStatus.VERIFIED,
        "warnings": (),
    }

    values.update(overrides)

    return CoordinationStudyResult(**values)


@pytest.mark.unit
def test_create_valid_warning() -> None:
    warning = make_warning()

    assert warning.code is CoordinationWarningCode.UNVERIFIED_ENTRY
    assert warning.message == "Catalogue entry is not verified."


@pytest.mark.unit
def test_warning_message_is_trimmed() -> None:
    warning = CoordinationWarning(
        code=CoordinationWarningCode.ENGINEERING_REVIEW_REQUIRED,
        message="  Engineering review required.  ",
    )

    assert warning.message == "Engineering review required."


@pytest.mark.unit
def test_create_valid_entry_evaluation() -> None:
    evaluation = make_evaluation()

    assert evaluation.entry_code == "SEL-001"
    assert evaluation.overall_match is True
    assert evaluation.fault_level_margin_ka == Decimal("5")


@pytest.mark.unit
def test_duplicate_entry_warning_codes_are_rejected() -> None:
    warning = make_warning()

    with pytest.raises(
        ValueError,
        match="entry warning codes must be unique",
    ):
        make_evaluation(
            warnings=(warning, warning),
        )


@pytest.mark.unit
def test_create_valid_coordination_result() -> None:
    result = make_result()

    assert result.code == "STUDY-001"
    assert result.matching_entries == 1
    assert result.status is CoordinationStudyStatus.VERIFIED


@pytest.mark.unit
def test_matching_entries_cannot_exceed_evaluated() -> None:
    with pytest.raises(
        ValueError,
        match="must not exceed evaluated_entries",
    ):
        make_result(
            evaluated_entries=1,
            matching_entries=2,
        )


@pytest.mark.unit
def test_entry_evaluation_count_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="count must equal evaluated_entries",
    ):
        make_result(
            entry_evaluations=(),
        )


@pytest.mark.unit
def test_no_match_rejects_selected_values() -> None:
    with pytest.raises(
        ValueError,
        match="must not contain selected entry values",
    ):
        make_result(
            status=CoordinationStudyStatus.NO_MATCH,
            matching_entries=0,
        )


@pytest.mark.unit
def test_matched_result_requires_complete_values() -> None:
    with pytest.raises(
        ValueError,
        match="requires complete selected entry values",
    ):
        make_result(
            selected_entry_code=None,
        )


@pytest.mark.unit
def test_duplicate_result_warning_codes_are_rejected() -> None:
    warning = make_warning()

    with pytest.raises(
        ValueError,
        match="result warning codes must be unique",
    ):
        make_result(
            status=CoordinationStudyStatus.WARNING,
            warnings=(warning, warning),
        )


@pytest.mark.unit
def test_valid_type_2_result() -> None:
    evaluation = make_evaluation(
        entry_code="T2-001",
        objective=CoordinationObjective.TYPE_2,
        starter_method=StarterMethod.DOL,
        motor_power_kw=Decimal("45"),
    )

    result = make_result(
        objective=CoordinationObjective.TYPE_2,
        selected_entry_code="T2-001",
        selected_starter_method=StarterMethod.DOL,
        selected_motor_power_kw=Decimal("45"),
        entry_evaluations=(evaluation,),
    )

    assert result.objective is CoordinationObjective.TYPE_2
    assert result.selected_starter_method is StarterMethod.DOL