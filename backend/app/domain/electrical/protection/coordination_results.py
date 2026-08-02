"""
Result models for protection coordination studies.
KESE-S2-M11 Phase-2
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.protection.coordination_models import (
    CoordinationObjective,
    CoordinationVerificationStatus,
    StarterMethod,
)
from app.domain.electrical.sources.common import (
    normalize_required_text,
)


class CoordinationStudyStatus(StrEnum):
    """Protection coordination study status."""

    VERIFIED = "VERIFIED"
    WARNING = "WARNING"
    NO_MATCH = "NO_MATCH"


class CoordinationWarningCode(StrEnum):
    """Structured coordination warning codes."""

    NO_MATCHING_ENTRY = "NO_MATCHING_ENTRY"
    FAULT_LEVEL_EXCEEDS_LIMIT = "FAULT_LEVEL_EXCEEDS_LIMIT"
    UNVERIFIED_ENTRY = "UNVERIFIED_ENTRY"
    MOTOR_POWER_MISMATCH = "MOTOR_POWER_MISMATCH"
    STARTER_METHOD_MISMATCH = "STARTER_METHOD_MISMATCH"
    DEVICE_PAIR_MISMATCH = "DEVICE_PAIR_MISMATCH"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class CoordinationWarning:
    """Structured coordination-study warning."""

    code: CoordinationWarningCode
    message: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.code,
            CoordinationWarningCode,
        ):
            raise TypeError(
                "code must be a CoordinationWarningCode value"
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
class CoordinationEntryEvaluation:
    """Evaluation result for one coordination catalogue entry."""

    entry_code: str
    objective: CoordinationObjective
    verification_status: CoordinationVerificationStatus

    device_pair_match: bool
    fault_level_adequate: bool
    starter_method_match: bool
    motor_power_adequate: bool
    overall_match: bool

    applicable_limit_ka: Decimal | None
    fault_level_margin_ka: Decimal | None

    starter_method: StarterMethod | None
    motor_power_kw: Decimal | None

    warnings: tuple[CoordinationWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "entry_code",
            normalize_required_text(
                "entry_code",
                self.entry_code,
            ),
        )

        for field_name, value in {
            "device_pair_match": self.device_pair_match,
            "fault_level_adequate": self.fault_level_adequate,
            "starter_method_match": self.starter_method_match,
            "motor_power_adequate": self.motor_power_adequate,
            "overall_match": self.overall_match,
        }.items():
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
                CoordinationWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only "
                "CoordinationWarning records"
            )

        warning_codes = tuple(
            warning.code
            for warning in self.warnings
        )

        if len(warning_codes) != len(
            set(warning_codes)
        ):
            raise ValueError(
                "entry warning codes must be unique"
            )


@dataclass(frozen=True, slots=True)
class CoordinationStudyResult:
    """Immutable protection coordination study result."""

    code: str
    name: str

    objective: CoordinationObjective
    prospective_fault_current_ka: Decimal

    evaluated_entries: int
    matching_entries: int

    selected_entry_code: str | None
    selected_verification_status: (
        CoordinationVerificationStatus | None
    )

    selected_limit_ka: Decimal | None
    fault_level_margin_ka: Decimal | None

    selected_starter_method: StarterMethod | None
    selected_motor_power_kw: Decimal | None

    coordination_verified: bool

    entry_evaluations: tuple[
        CoordinationEntryEvaluation,
        ...,
    ]

    status: CoordinationStudyStatus
    warnings: tuple[CoordinationWarning, ...]

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
            "evaluated_entries": self.evaluated_entries,
            "matching_entries": self.matching_entries,
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

        if self.matching_entries > self.evaluated_entries:
            raise ValueError(
                "matching_entries must not exceed "
                "evaluated_entries"
            )

        if not isinstance(
            self.coordination_verified,
            bool,
        ):
            raise TypeError(
                "coordination_verified must be a boolean"
            )

        if not isinstance(
            self.entry_evaluations,
            tuple,
        ):
            raise TypeError(
                "entry_evaluations must be a tuple"
            )

        if not all(
            isinstance(
                evaluation,
                CoordinationEntryEvaluation,
            )
            for evaluation in self.entry_evaluations
        ):
            raise TypeError(
                "entry_evaluations must contain only "
                "CoordinationEntryEvaluation records"
            )

        if (
            len(self.entry_evaluations)
            != self.evaluated_entries
        ):
            raise ValueError(
                "entry_evaluations count must equal "
                "evaluated_entries"
            )

        if not isinstance(
            self.status,
            CoordinationStudyStatus,
        ):
            raise TypeError(
                "status must be a CoordinationStudyStatus value"
            )

        selected_values = (
            self.selected_entry_code,
            self.selected_verification_status,
            self.selected_limit_ka,
            self.fault_level_margin_ka,
        )

        if self.status is CoordinationStudyStatus.NO_MATCH:
            if any(
                value is not None
                for value in selected_values
            ):
                raise ValueError(
                    "NO_MATCH result must not contain "
                    "selected entry values"
                )
        elif any(
            value is None
            for value in selected_values
        ):
            raise ValueError(
                "matched coordination result requires complete "
                "selected entry values"
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
                CoordinationWarning,
            )
            for warning in self.warnings
        ):
            raise TypeError(
                "warnings must contain only "
                "CoordinationWarning records"
            )

        warning_codes = tuple(
            warning.code
            for warning in self.warnings
        )

        if len(warning_codes) != len(
            set(warning_codes)
        ):
            raise ValueError(
                "result warning codes must be unique"
            )


__all__ = [
    "CoordinationEntryEvaluation",
    "CoordinationStudyResult",
    "CoordinationStudyStatus",
    "CoordinationWarning",
    "CoordinationWarningCode",
]