"""
Pure domain engine for intelligent switchgear selection.
KESE-S2-M11
"""

from decimal import Decimal, ROUND_HALF_UP

from app.domain.electrical.protection.switchgear_models import (
    CoordinationType,
    ManufacturerSource,
    SwitchgearCandidate,
    SwitchgearSelectionInput,
)
from app.domain.electrical.protection.switchgear_results import (
    SwitchgearCandidateEvaluation,
    SwitchgearSelectionResult,
    SwitchgearSelectionStatus,
    SwitchgearWarning,
    SwitchgearWarningCode,
)

DECIMAL_QUANTUM = Decimal("0.0001")
LOW_MARGIN_FACTOR = Decimal("1.25")


def _round_value(
    value: Decimal,
) -> Decimal:
    """Round engineering values to four decimal places."""

    return value.quantize(
        DECIMAL_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _evaluate_candidate(
    sizing_input: SwitchgearSelectionInput,
    candidate: SwitchgearCandidate,
) -> SwitchgearCandidateEvaluation:
    """Evaluate one switchgear candidate."""

    current_margin_a = (
        candidate.rated_current_a
        - sizing_input.design_current_a
    )

    icu_margin_ka = (
        candidate.ultimate_breaking_capacity_ka
        - sizing_input.prospective_short_circuit_current_ka
    )

    ics_margin_ka = (
        candidate.service_breaking_capacity_ka
        - sizing_input.prospective_short_circuit_current_ka
    )

    icw_margin_ka = (
        candidate.short_time_withstand_current_ka
        - sizing_input.minimum_short_time_withstand_current_ka
    )

    current_adequate = (
        candidate.rated_current_a
        >= sizing_input.design_current_a
    )

    voltage_adequate = (
        candidate.rated_operational_voltage_v
        >= sizing_input.system_voltage_v
    )

    icu_adequate = (
        candidate.ultimate_breaking_capacity_ka
        >= sizing_input.prospective_short_circuit_current_ka
    )

    ics_adequate = (
        candidate.service_breaking_capacity_ka
        >= sizing_input.prospective_short_circuit_current_ka
    )

    icw_adequate = (
        candidate.short_time_withstand_current_ka
        >= sizing_input.minimum_short_time_withstand_current_ka
    )

    pole_count_adequate = (
        candidate.number_of_poles
        == sizing_input.number_of_poles
    )

    service_breaking_ratio_adequate = (
        candidate.service_breaking_ratio
        >= sizing_input.minimum_service_breaking_ratio
    )

    overall_adequate = all(
        (
            candidate.device_type
            is sizing_input.required_device_type,
            current_adequate,
            voltage_adequate,
            icu_adequate,
            ics_adequate,
            icw_adequate,
            pole_count_adequate,
            service_breaking_ratio_adequate,
        )
    )

    warnings: list[SwitchgearWarning] = []

    if current_adequate and (
        candidate.rated_current_a
        < sizing_input.design_current_a
        * LOW_MARGIN_FACTOR
    ):
        warnings.append(
            SwitchgearWarning(
                code=(
                    SwitchgearWarningCode
                    .LOW_CURRENT_MARGIN
                ),
                message=(
                    "Selected device current margin is "
                    "below 25 percent."
                ),
            )
        )

    if icu_adequate and (
        candidate.ultimate_breaking_capacity_ka
        < sizing_input.prospective_short_circuit_current_ka
        * LOW_MARGIN_FACTOR
    ):
        warnings.append(
            SwitchgearWarning(
                code=SwitchgearWarningCode.LOW_ICU_MARGIN,
                message=(
                    "Selected device Icu margin is "
                    "below 25 percent."
                ),
            )
        )

    if ics_adequate and (
        candidate.service_breaking_capacity_ka
        < sizing_input.prospective_short_circuit_current_ka
        * LOW_MARGIN_FACTOR
    ):
        warnings.append(
            SwitchgearWarning(
                code=SwitchgearWarningCode.LOW_ICS_MARGIN,
                message=(
                    "Selected device Ics margin is "
                    "below 25 percent."
                ),
            )
        )

    if (
        icw_adequate
        and sizing_input
        .minimum_short_time_withstand_current_ka
        > Decimal("0")
        and candidate.short_time_withstand_current_ka
        < sizing_input
        .minimum_short_time_withstand_current_ka
        * LOW_MARGIN_FACTOR
    ):
        warnings.append(
            SwitchgearWarning(
                code=SwitchgearWarningCode.LOW_ICW_MARGIN,
                message=(
                    "Selected device Icw margin is "
                    "below 25 percent."
                ),
            )
        )

    return SwitchgearCandidateEvaluation(
        code=candidate.code,
        family=candidate.family,
        manufacturer=candidate.manufacturer,
        device_type=candidate.device_type,
        trip_unit_type=candidate.trip_unit_type,
        current_adequate=current_adequate,
        voltage_adequate=voltage_adequate,
        icu_adequate=icu_adequate,
        ics_adequate=ics_adequate,
        icw_adequate=icw_adequate,
        pole_count_adequate=pole_count_adequate,
        service_breaking_ratio_adequate=(
            service_breaking_ratio_adequate
        ),
        overall_adequate=overall_adequate,
        current_margin_a=_round_value(
            current_margin_a
        ),
        icu_margin_ka=_round_value(
            icu_margin_ka
        ),
        ics_margin_ka=_round_value(
            ics_margin_ka
        ),
        icw_margin_ka=_round_value(
            icw_margin_ka
        ),
        warnings=tuple(warnings),
    )


def calculate_switchgear_selection(
    sizing_input: SwitchgearSelectionInput,
) -> SwitchgearSelectionResult:
    """Evaluate candidates and select the smallest adequate device."""

    if not isinstance(
        sizing_input,
        SwitchgearSelectionInput,
    ):
        raise TypeError(
            "sizing_input must be a "
            "SwitchgearSelectionInput record"
        )

    evaluations = tuple(
        _evaluate_candidate(
            sizing_input,
            candidate,
        )
        for candidate in sizing_input.candidates
    )

    adequate_pairs = tuple(
        (
            candidate,
            evaluation,
        )
        for candidate, evaluation in zip(
            sizing_input.candidates,
            evaluations,
            strict=True,
        )
        if evaluation.overall_adequate
    )

    coordination_verified = (
        sizing_input.coordination_type
        is CoordinationType.NONE
    )

    manufacturer_reference_used = any(
        candidate.manufacturer
        is not ManufacturerSource.MANUFACTURER_NEUTRAL
        and candidate.reference_document is not None
        for candidate in sizing_input.candidates
    )

    warnings: list[SwitchgearWarning] = []

    if (
        sizing_input.coordination_type
        is not CoordinationType.NONE
    ):
        warnings.append(
            SwitchgearWarning(
                code=(
                    SwitchgearWarningCode
                    .COORDINATION_NOT_VERIFIED
                ),
                message=(
                    "Requested coordination requires verified "
                    "manufacturer selectivity or coordination data."
                ),
            )
        )

    if (
        sizing_input.manufacturer_reference_required
        and not manufacturer_reference_used
    ):
        warnings.append(
            SwitchgearWarning(
                code=(
                    SwitchgearWarningCode
                    .MANUFACTURER_REFERENCE_REQUIRED
                ),
                message=(
                    "A verified manufacturer reference is required "
                    "for this selection."
                ),
            )
        )

    if sizing_input.protection_settings is None:
        warnings.append(
            SwitchgearWarning(
                code=(
                    SwitchgearWarningCode
                    .PROTECTION_SETTINGS_REVIEW_REQUIRED
                ),
                message=(
                    "Protection settings have not been provided "
                    "and require engineering review."
                ),
            )
        )

    if not adequate_pairs:
        warnings.append(
            SwitchgearWarning(
                code=(
                    SwitchgearWarningCode
                    .NO_SUITABLE_DEVICE
                ),
                message=(
                    "No switchgear candidate satisfies all "
                    "selection requirements."
                ),
            )
        )

        return SwitchgearSelectionResult(
            code=sizing_input.code,
            name=sizing_input.name,
            application=sizing_input.application,
            required_device_type=(
                sizing_input.required_device_type
            ),
            coordination_type=sizing_input.coordination_type,
            system_voltage_v=sizing_input.system_voltage_v,
            design_current_a=sizing_input.design_current_a,
            prospective_short_circuit_current_ka=(
                sizing_input
                .prospective_short_circuit_current_ka
            ),
            evaluated_candidates=len(evaluations),
            adequate_candidates=0,
            selected_candidate_code=None,
            selected_candidate_family=None,
            selected_manufacturer=None,
            selected_frame_current_a=None,
            selected_rated_current_a=None,
            selected_icu_ka=None,
            selected_ics_ka=None,
            selected_icw_ka=None,
            current_margin_a=None,
            icu_margin_ka=None,
            ics_margin_ka=None,
            icw_margin_ka=None,
            coordination_verified=coordination_verified,
            manufacturer_reference_used=(
                manufacturer_reference_used
            ),
            candidate_evaluations=evaluations,
            status=SwitchgearSelectionStatus.NO_SOLUTION,
            warnings=tuple(warnings),
        )

    selected_candidate, selected_evaluation = min(
        adequate_pairs,
        key=lambda pair: (
            pair[0].rated_current_a,
            pair[0].frame_current_a,
            pair[0].ultimate_breaking_capacity_ka,
            pair[0].code,
        ),
    )

    warnings.extend(
        selected_evaluation.warnings
    )

    status = (
        SwitchgearSelectionStatus.WARNING
        if warnings
        else SwitchgearSelectionStatus.SELECTED
    )

    return SwitchgearSelectionResult(
        code=sizing_input.code,
        name=sizing_input.name,
        application=sizing_input.application,
        required_device_type=(
            sizing_input.required_device_type
        ),
        coordination_type=(
            sizing_input.coordination_type
        ),
        system_voltage_v=(
            sizing_input.system_voltage_v
        ),
        design_current_a=(
            sizing_input.design_current_a
        ),
        prospective_short_circuit_current_ka=(
            sizing_input
            .prospective_short_circuit_current_ka
        ),
        evaluated_candidates=len(evaluations),
        adequate_candidates=len(adequate_pairs),
        selected_candidate_code=(
            selected_candidate.code
        ),
        selected_candidate_family=(
            selected_candidate.family
        ),
        selected_manufacturer=(
            selected_candidate.manufacturer
        ),
        selected_frame_current_a=(
            selected_candidate.frame_current_a
        ),
        selected_rated_current_a=(
            selected_candidate.rated_current_a
        ),
        selected_icu_ka=(
            selected_candidate
            .ultimate_breaking_capacity_ka
        ),
        selected_ics_ka=(
            selected_candidate
            .service_breaking_capacity_ka
        ),
        selected_icw_ka=(
            selected_candidate
            .short_time_withstand_current_ka
        ),
        current_margin_a=(
            selected_evaluation.current_margin_a
        ),
        icu_margin_ka=(
            selected_evaluation.icu_margin_ka
        ),
        ics_margin_ka=(
            selected_evaluation.ics_margin_ka
        ),
        icw_margin_ka=(
            selected_evaluation.icw_margin_ka
        ),
        coordination_verified=(
            coordination_verified
        ),
        manufacturer_reference_used=(
            selected_candidate.manufacturer
            is not ManufacturerSource.MANUFACTURER_NEUTRAL
            and selected_candidate.reference_document
            is not None
        ),
        candidate_evaluations=evaluations,
        status=status,
        warnings=tuple(warnings),
    )


__all__ = [
    "calculate_switchgear_selection",
]
