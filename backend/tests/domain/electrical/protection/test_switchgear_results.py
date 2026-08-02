"""
Unit tests for intelligent switchgear selection results.
KESE-S2-M11
"""

from decimal import Decimal

import pytest

from app.domain.electrical.protection.switchgear_models import (
    CoordinationType,
    ManufacturerSource,
    SwitchgearApplication,
    SwitchgearDeviceType,
    SwitchgearTripUnitType,
)
from app.domain.electrical.protection.switchgear_results import (
    SwitchgearCandidateEvaluation,
    SwitchgearSelectionResult,
    SwitchgearSelectionStatus,
    SwitchgearWarning,
    SwitchgearWarningCode,
)


def make_warning() -> SwitchgearWarning:
    return SwitchgearWarning(
        code=SwitchgearWarningCode.LOW_ICU_MARGIN,
        message="Icu margin is low.",
    )


def make_evaluation(
    **overrides: object,
) -> SwitchgearCandidateEvaluation:
    values: dict[str, object] = {
        "code": "ACB-1600-65",
        "family": "Master Range",
        "manufacturer": ManufacturerSource.MANUFACTURER_NEUTRAL,
        "device_type": SwitchgearDeviceType.ACB,
        "trip_unit_type": SwitchgearTripUnitType.ELECTRONIC_LSIG,
        "current_adequate": True,
        "voltage_adequate": True,
        "icu_adequate": True,
        "ics_adequate": True,
        "icw_adequate": True,
        "pole_count_adequate": True,
        "service_breaking_ratio_adequate": True,
        "overall_adequate": True,
        "current_margin_a": Decimal("200"),
        "icu_margin_ka": Decimal("15"),
        "ics_margin_ka": Decimal("15"),
        "icw_margin_ka": Decimal("15"),
        "warnings": (),
    }

    values.update(overrides)

    return SwitchgearCandidateEvaluation(**values)


def make_result(
    **overrides: object,
) -> SwitchgearSelectionResult:
    evaluation = make_evaluation()

    values: dict[str, object] = {
        "code": "SEL-001",
        "name": "Main PCC Incomer",
        "application": SwitchgearApplication.INCOMER,
        "required_device_type": SwitchgearDeviceType.ACB,
        "coordination_type": CoordinationType.NONE,
        "system_voltage_v": Decimal("415"),
        "design_current_a": Decimal("1400"),
        "prospective_short_circuit_current_ka": Decimal("50"),
        "evaluated_candidates": 1,
        "adequate_candidates": 1,
        "selected_candidate_code": "ACB-1600-65",
        "selected_candidate_family": "Master Range",
        "selected_manufacturer": (
            ManufacturerSource.MANUFACTURER_NEUTRAL
        ),
        "selected_frame_current_a": Decimal("1600"),
        "selected_rated_current_a": Decimal("1600"),
        "selected_icu_ka": Decimal("65"),
        "selected_ics_ka": Decimal("65"),
        "selected_icw_ka": Decimal("65"),
        "current_margin_a": Decimal("200"),
        "icu_margin_ka": Decimal("15"),
        "ics_margin_ka": Decimal("15"),
        "icw_margin_ka": Decimal("15"),
        "coordination_verified": True,
        "manufacturer_reference_used": False,
        "candidate_evaluations": (evaluation,),
        "status": SwitchgearSelectionStatus.SELECTED,
        "warnings": (),
    }

    values.update(overrides)

    return SwitchgearSelectionResult(**values)


@pytest.mark.unit
def test_create_valid_candidate_evaluation() -> None:
    evaluation = make_evaluation()

    assert evaluation.code == "ACB-1600-65"
    assert evaluation.overall_adequate is True
    assert evaluation.current_margin_a == Decimal("200")


@pytest.mark.unit
def test_candidate_text_is_trimmed() -> None:
    evaluation = make_evaluation(
        code="  ACB-1600-65  ",
        family="  Master Range  ",
    )

    assert evaluation.code == "ACB-1600-65"
    assert evaluation.family == "Master Range"


@pytest.mark.unit
def test_duplicate_candidate_warning_codes_are_rejected() -> None:
    warning = make_warning()

    with pytest.raises(
        ValueError,
        match="candidate warning codes must be unique",
    ):
        make_evaluation(
            warnings=(warning, warning),
        )


@pytest.mark.unit
def test_create_valid_switchgear_result() -> None:
    result = make_result()

    assert result.code == "SEL-001"
    assert result.adequate_candidates == 1
    assert result.status is SwitchgearSelectionStatus.SELECTED


@pytest.mark.unit
def test_adequate_candidates_cannot_exceed_evaluated() -> None:
    with pytest.raises(
        ValueError,
        match="must not exceed evaluated_candidates",
    ):
        make_result(
            evaluated_candidates=1,
            adequate_candidates=2,
        )


@pytest.mark.unit
def test_candidate_evaluation_count_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="count must equal evaluated_candidates",
    ):
        make_result(
            candidate_evaluations=(),
        )


@pytest.mark.unit
def test_no_solution_rejects_selected_values() -> None:
    with pytest.raises(
        ValueError,
        match="must not contain selected device values",
    ):
        make_result(
            status=SwitchgearSelectionStatus.NO_SOLUTION,
        )


@pytest.mark.unit
def test_selected_result_requires_complete_values() -> None:
    with pytest.raises(
        ValueError,
        match="requires complete selected device values",
    ):
        make_result(
            selected_candidate_code=None,
        )


@pytest.mark.unit
def test_duplicate_result_warning_codes_are_rejected() -> None:
    warning = make_warning()

    with pytest.raises(
        ValueError,
        match="result warning codes must be unique",
    ):
        make_result(
            status=SwitchgearSelectionStatus.WARNING,
            warnings=(warning, warning),
        )
