"""
Pure domain engine for protection coordination studies.
KESE-S2-M11 Phase-2
"""

from decimal import Decimal, ROUND_HALF_UP

from app.domain.electrical.protection.coordination_models import (
    CoordinationCatalogueEntry,
    CoordinationObjective,
    CoordinationStudyInput,
    CoordinationVerificationStatus,
)
from app.domain.electrical.protection.coordination_results import (
    CoordinationEntryEvaluation,
    CoordinationStudyResult,
    CoordinationStudyStatus,
    CoordinationWarning,
    CoordinationWarningCode,
)


DECIMAL_QUANTUM = Decimal("0.0001")


def _round_value(
    value: Decimal,
) -> Decimal:
    """Round engineering values to four decimal places."""

    return value.quantize(
        DECIMAL_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _device_pair_matches(
    sizing_input: CoordinationStudyInput,
    entry: CoordinationCatalogueEntry,
) -> bool:
    """Check upstream and downstream device-code matching."""

    return (
        entry.upstream_device.code == sizing_input.upstream_device.code
        and entry.downstream_device.code == sizing_input.downstream_device.code
    )


def _applicable_limit(
    entry: CoordinationCatalogueEntry,
) -> Decimal | None:
    """Return the applicable fault-current limit."""

    if entry.objective is CoordinationObjective.SELECTIVITY:
        return entry.maximum_selective_current_ka

    if entry.objective is CoordinationObjective.CASCADING:
        return entry.maximum_cascading_fault_level_ka

    return entry.downstream_device.breaking_capacity_ka


def _evaluate_entry(
    sizing_input: CoordinationStudyInput,
    entry: CoordinationCatalogueEntry,
) -> CoordinationEntryEvaluation:
    """Evaluate one coordination catalogue entry."""

    device_pair_match = _device_pair_matches(
        sizing_input,
        entry,
    )

    objective_match = entry.objective is sizing_input.objective

    applicable_limit_ka = _applicable_limit(entry)

    fault_level_adequate = (
        applicable_limit_ka is not None
        and applicable_limit_ka >= sizing_input.prospective_fault_current_ka
    )

    fault_level_margin_ka = (
        applicable_limit_ka - sizing_input.prospective_fault_current_ka
        if applicable_limit_ka is not None
        else None
    )

    starter_method_match = True
    motor_power_adequate = True

    if sizing_input.objective in {
        CoordinationObjective.TYPE_1,
        CoordinationObjective.TYPE_2,
    }:
        starter_method_match = entry.starter_method is sizing_input.required_starter_method

        motor_power_adequate = (
            entry.motor_power_kw is not None
            and sizing_input.required_motor_power_kw is not None
            and entry.motor_power_kw >= sizing_input.required_motor_power_kw
        )

    verification_adequate = (
        not sizing_input.require_verified_entry
        or entry.verification_status is CoordinationVerificationStatus.VERIFIED
    )

    overall_match = all(
        (
            objective_match,
            device_pair_match,
            fault_level_adequate,
            starter_method_match,
            motor_power_adequate,
            verification_adequate,
        )
    )

    warnings: list[CoordinationWarning] = []

    if not device_pair_match:
        warnings.append(
            CoordinationWarning(
                code=(CoordinationWarningCode.DEVICE_PAIR_MISMATCH),
                message=(
                    "Catalogue device pair does not match "
                    "the requested upstream and downstream devices."
                ),
            )
        )

    if not fault_level_adequate:
        warnings.append(
            CoordinationWarning(
                code=(CoordinationWarningCode.FAULT_LEVEL_EXCEEDS_LIMIT),
                message=("Prospective fault current exceeds the applicable coordination limit."),
            )
        )
    if entry.verification_status is not CoordinationVerificationStatus.VERIFIED:
        warnings.append(
            CoordinationWarning(
                code=CoordinationWarningCode.UNVERIFIED_ENTRY,
                message=("Coordination catalogue entry is not manufacturer-verified."),
            )
        )

    if not starter_method_match:
        warnings.append(
            CoordinationWarning(
                code=(CoordinationWarningCode.STARTER_METHOD_MISMATCH),
                message=(
                    "Catalogue starter method does not match the required motor starting method."
                ),
            )
        )

    if not motor_power_adequate:
        warnings.append(
            CoordinationWarning(
                code=(CoordinationWarningCode.MOTOR_POWER_MISMATCH),
                message=("Catalogue motor-power rating is below the required motor power."),
            )
        )

    return CoordinationEntryEvaluation(
        entry_code=entry.code,
        objective=entry.objective,
        verification_status=entry.verification_status,
        device_pair_match=device_pair_match,
        fault_level_adequate=fault_level_adequate,
        starter_method_match=starter_method_match,
        motor_power_adequate=motor_power_adequate,
        overall_match=overall_match,
        applicable_limit_ka=(
            _round_value(applicable_limit_ka) if applicable_limit_ka is not None else None
        ),
        fault_level_margin_ka=(
            _round_value(fault_level_margin_ka) if fault_level_margin_ka is not None else None
        ),
        starter_method=entry.starter_method,
        motor_power_kw=entry.motor_power_kw,
        warnings=tuple(warnings),
    )


def calculate_coordination_study(
    sizing_input: CoordinationStudyInput,
) -> CoordinationStudyResult:
    """Evaluate catalogue entries and select the best match."""

    if not isinstance(
        sizing_input,
        CoordinationStudyInput,
    ):
        raise TypeError("sizing_input must be a CoordinationStudyInput record")

    evaluations = tuple(
        _evaluate_entry(
            sizing_input,
            entry,
        )
        for entry in sizing_input.catalogue_entries
    )

    matching_pairs = tuple(
        (
            entry,
            evaluation,
        )
        for entry, evaluation in zip(
            sizing_input.catalogue_entries,
            evaluations,
            strict=True,
        )
        if evaluation.overall_match
    )

    warnings: list[CoordinationWarning] = []

    if not matching_pairs:
        warnings.append(
            CoordinationWarning(
                code=(CoordinationWarningCode.NO_MATCHING_ENTRY),
                message=("No coordination catalogue entry satisfies all study requirements."),
            )
        )

        warnings.append(
            CoordinationWarning(
                code=(CoordinationWarningCode.ENGINEERING_REVIEW_REQUIRED),
                message=("Protection coordination requires engineering review."),
            )
        )

        return CoordinationStudyResult(
            code=sizing_input.code,
            name=sizing_input.name,
            objective=sizing_input.objective,
            prospective_fault_current_ka=(sizing_input.prospective_fault_current_ka),
            evaluated_entries=len(evaluations),
            matching_entries=0,
            selected_entry_code=None,
            selected_verification_status=None,
            selected_limit_ka=None,
            fault_level_margin_ka=None,
            selected_starter_method=None,
            selected_motor_power_kw=None,
            coordination_verified=False,
            entry_evaluations=evaluations,
            status=CoordinationStudyStatus.NO_MATCH,
            warnings=tuple(warnings),
        )
    selected_entry, selected_evaluation = min(
        matching_pairs,
        key=lambda pair: (
            pair[1].fault_level_margin_ka
            if pair[1].fault_level_margin_ka is not None
            else Decimal("Infinity"),
            pair[0].code,
        ),
    )

    selected_verified = (
        selected_entry.verification_status is CoordinationVerificationStatus.VERIFIED
    )

    if not selected_verified:
        warnings.append(
            CoordinationWarning(
                code=CoordinationWarningCode.UNVERIFIED_ENTRY,
                message=("Selected coordination entry is not manufacturer-verified."),
            )
        )

        warnings.append(
            CoordinationWarning(
                code=(CoordinationWarningCode.ENGINEERING_REVIEW_REQUIRED),
                message=("Selected coordination entry requires engineering review."),
            )
        )

    status = (
        CoordinationStudyStatus.VERIFIED if selected_verified else CoordinationStudyStatus.WARNING
    )

    return CoordinationStudyResult(
        code=sizing_input.code,
        name=sizing_input.name,
        objective=sizing_input.objective,
        prospective_fault_current_ka=(sizing_input.prospective_fault_current_ka),
        evaluated_entries=len(evaluations),
        matching_entries=len(matching_pairs),
        selected_entry_code=selected_entry.code,
        selected_verification_status=(selected_entry.verification_status),
        selected_limit_ka=(selected_evaluation.applicable_limit_ka),
        fault_level_margin_ka=(selected_evaluation.fault_level_margin_ka),
        selected_starter_method=(selected_entry.starter_method),
        selected_motor_power_kw=(selected_entry.motor_power_kw),
        coordination_verified=selected_verified,
        entry_evaluations=evaluations,
        status=status,
        warnings=tuple(warnings),
    )


__all__ = [
    "calculate_coordination_study",
]
