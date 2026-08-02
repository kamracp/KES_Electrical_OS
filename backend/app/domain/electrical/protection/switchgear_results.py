"""
Result models for intelligent switchgear selection.
KESE-S2-M11
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.protection.switchgear_models import (
    CoordinationType,
    ManufacturerSource,
    SwitchgearApplication,
    SwitchgearDeviceType,
    SwitchgearTripUnitType,
)
from app.domain.electrical.sources.common import (
    normalize_required_text,
)


class SwitchgearSelectionStatus(StrEnum):
    """Switchgear selection result status."""

    SELECTED = "SELECTED"
    WARNING = "WARNING"
    NO_SOLUTION = "NO_SOLUTION"


class SwitchgearWarningCode(StrEnum):
    """Structured switchgear engineering warning codes."""

    LOW_CURRENT_MARGIN = "LOW_CURRENT_MARGIN"
    LOW_ICU_MARGIN = "LOW_ICU_MARGIN"
    LOW_ICS_MARGIN = "LOW_ICS_MARGIN"
    LOW_ICW_MARGIN = "LOW_ICW_MARGIN"
    COORDINATION_NOT_VERIFIED = "COORDINATION_NOT_VERIFIED"
    MANUFACTURER_REFERENCE_REQUIRED = (
        "MANUFACTURER_REFERENCE_REQUIRED"
    )
    PROTECTION_SETTINGS_REVIEW_REQUIRED = (
        "PROTECTION_SETTINGS_REVIEW_REQUIRED"
    )
    NO_SUITABLE_DEVICE = "NO_SUITABLE_DEVICE"


@dataclass(frozen=True, slots=True)
class SwitchgearWarning:
    """Structured switchgear selection warning."""

    code: SwitchgearWarningCode
    message: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.code,
            SwitchgearWarningCode,
        ):
            raise TypeError(
                "code must be a SwitchgearWarningCode value"
            )

        object.__setattr__(
            self,
            "message",
            normalize_required_text(
                "message",
                self.message,
            ),
        )


@dataclass(frozen=True, slots=True)
class SwitchgearCandidateEvaluation:
    """Evaluation result for one switchgear candidate."""

    code: str
    family: str
    manufacturer: ManufacturerSource

    device_type: SwitchgearDeviceType
    trip_unit_type: SwitchgearTripUnitType

    current_adequate: bool
    voltage_adequate: bool
    icu_adequate: bool
    ics_adequate: bool
    icw_adequate: bool
    pole_count_adequate: bool
    service_breaking_ratio_adequate: bool

    overall_adequate: bool

    current_margin_a: Decimal
    icu_margin_ka: Decimal
    ics_margin_ka: Decimal
    icw_margin_ka: Decimal

    warnings: tuple[SwitchgearWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            normalize_required_text(
                "code",
                self.code,
            ),
        )
        object.__setattr__(
            self,
            "family",
            normalize_required_text(
                "family",
                self.family,
            ),
        )

        boolean_fields = {
            "current_adequate": self.current_adequate,
            "voltage_adequate": self.voltage_adequate,
            "icu_adequate": self.icu_adequate,
            "ics_adequate": self.ics_adequate,
            "icw_adequate": self.icw_adequate,
            "pole_count_adequate": self.pole_count_adequate,
            "service_breaking_ratio_adequate": (
                self.service_breaking_ratio_adequate
            ),
            "overall_adequate": self.overall_adequate,
        }

        for field_name, value in boolean_fields.items():
            if not isinstance(value, bool):
                raise TypeError(
                    f"{field_name} must be a boolean"
                )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        if not all(
            isinstance(
                warning,
                SwitchgearWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only "
                "SwitchgearWarning records"
            )

        warning_codes = tuple(
            warning.code
            for warning in self.warnings
        )

        if len(warning_codes) != len(set(warning_codes)):
            raise ValueError(
                "candidate warning codes must be unique"
            )


@dataclass(frozen=True, slots=True)
class SwitchgearSelectionResult:
    """Immutable switchgear selection result."""

    code: str
    name: str

    application: SwitchgearApplication
    required_device_type: SwitchgearDeviceType
    coordination_type: CoordinationType

    system_voltage_v: Decimal
    design_current_a: Decimal
    prospective_short_circuit_current_ka: Decimal

    evaluated_candidates: int
    adequate_candidates: int

    selected_candidate_code: str | None
    selected_candidate_family: str | None
    selected_manufacturer: ManufacturerSource | None

    selected_frame_current_a: Decimal | None
    selected_rated_current_a: Decimal | None
    selected_icu_ka: Decimal | None
    selected_ics_ka: Decimal | None
    selected_icw_ka: Decimal | None

    current_margin_a: Decimal | None
    icu_margin_ka: Decimal | None
    ics_margin_ka: Decimal | None
    icw_margin_ka: Decimal | None

    coordination_verified: bool
    manufacturer_reference_used: bool

    candidate_evaluations: tuple[
        SwitchgearCandidateEvaluation,
        ...,
    ]

    status: SwitchgearSelectionStatus
    warnings: tuple[SwitchgearWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            normalize_required_text(
                "code",
                self.code,
            ),
        )
        object.__setattr__(
            self,
            "name",
            normalize_required_text(
                "name",
                self.name,
            ),
        )

        for field_name, value in {
            "evaluated_candidates": self.evaluated_candidates,
            "adequate_candidates": self.adequate_candidates,
        }.items():
            if isinstance(value, bool) or not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{field_name} must be an integer"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        if (
            self.adequate_candidates
            > self.evaluated_candidates
        ):
            raise ValueError(
                "adequate_candidates must not exceed "
                "evaluated_candidates"
            )

        if not isinstance(
            self.coordination_verified,
            bool,
        ):
            raise TypeError(
                "coordination_verified must be a boolean"
            )

        if not isinstance(
            self.manufacturer_reference_used,
            bool,
        ):
            raise TypeError(
                "manufacturer_reference_used must be a boolean"
            )

        if not isinstance(
            self.candidate_evaluations,
            tuple,
        ):
            raise TypeError(
                "candidate_evaluations must be a tuple"
            )

        if not all(
            isinstance(
                evaluation,
                SwitchgearCandidateEvaluation,
            )
            for evaluation in self.candidate_evaluations
        ):
            raise TypeError(
                "candidate_evaluations must contain only "
                "SwitchgearCandidateEvaluation records"
            )

        if (
            len(self.candidate_evaluations)
            != self.evaluated_candidates
        ):
            raise ValueError(
                "candidate_evaluations count must equal "
                "evaluated_candidates"
            )

        if not isinstance(
            self.status,
            SwitchgearSelectionStatus,
        ):
            raise TypeError(
                "status must be a "
                "SwitchgearSelectionStatus value"
            )

        selected_values = (
            self.selected_candidate_code,
            self.selected_candidate_family,
            self.selected_manufacturer,
            self.selected_frame_current_a,
            self.selected_rated_current_a,
            self.selected_icu_ka,
            self.selected_ics_ka,
            self.selected_icw_ka,
            self.current_margin_a,
            self.icu_margin_ka,
            self.ics_margin_ka,
            self.icw_margin_ka,
        )

        if (
            self.status
            is SwitchgearSelectionStatus.NO_SOLUTION
        ):
            if any(
                value is not None
                for value in selected_values
            ):
                raise ValueError(
                    "NO_SOLUTION result must not contain "
                    "selected device values"
                )
        elif any(
            value is None
            for value in selected_values
        ):
            raise ValueError(
                "selected switchgear result requires complete "
                "selected device values"
            )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        if not all(
            isinstance(
                warning,
                SwitchgearWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only "
                "SwitchgearWarning records"
            )

        warning_codes = tuple(
            warning.code
            for warning in self.warnings
        )

        if len(warning_codes) != len(set(warning_codes)):
            raise ValueError(
                "result warning codes must be unique"
            )


__all__ = [
    "SwitchgearCandidateEvaluation",
    "SwitchgearSelectionResult",
    "SwitchgearSelectionStatus",
    "SwitchgearWarning",
    "SwitchgearWarningCode",
]
