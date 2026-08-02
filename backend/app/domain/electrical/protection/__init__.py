"""
Protection engineering domain.
KESE-S2-M11
"""

from .coordination_engine import (
    calculate_coordination_study,
)
from .coordination_models import (
    CoordinationCatalogueEntry,
    CoordinationDeviceReference,
    CoordinationObjective,
    CoordinationStudyInput,
    CoordinationVerificationStatus,
    StarterMethod,
)
from .coordination_results import (
    CoordinationEntryEvaluation,
    CoordinationStudyResult,
    CoordinationStudyStatus,
    CoordinationWarning,
    CoordinationWarningCode,
)
from .switchgear_engine import (
    calculate_switchgear_selection,
)
from .switchgear_models import (
    CoordinationType,
    ManufacturerSource,
    ProtectionSettingsInput,
    SwitchgearApplication,
    SwitchgearCandidate,
    SwitchgearDeviceType,
    SwitchgearSelectionInput,
    SwitchgearTripUnitType,
)
from .switchgear_results import (
    SwitchgearCandidateEvaluation,
    SwitchgearSelectionResult,
    SwitchgearSelectionStatus,
    SwitchgearWarning,
    SwitchgearWarningCode,
)


__all__ = [
    "calculate_coordination_study",
    "calculate_switchgear_selection",
    "CoordinationCatalogueEntry",
    "CoordinationDeviceReference",
    "CoordinationEntryEvaluation",
    "CoordinationObjective",
    "CoordinationStudyInput",
    "CoordinationStudyResult",
    "CoordinationStudyStatus",
    "CoordinationType",
    "CoordinationVerificationStatus",
    "CoordinationWarning",
    "CoordinationWarningCode",
    "ManufacturerSource",
    "ProtectionSettingsInput",
    "StarterMethod",
    "SwitchgearApplication",
    "SwitchgearCandidate",
    "SwitchgearCandidateEvaluation",
    "SwitchgearDeviceType",
    "SwitchgearSelectionInput",
    "SwitchgearSelectionResult",
    "SwitchgearSelectionStatus",
    "SwitchgearTripUnitType",
    "SwitchgearWarning",
    "SwitchgearWarningCode",
]
