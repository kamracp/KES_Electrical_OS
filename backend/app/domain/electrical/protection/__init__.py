
"""
Protection engineering domain.
KESE-S2-M11
"""

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
    "calculate_switchgear_selection",
    "CoordinationType",
    "ManufacturerSource",
    "ProtectionSettingsInput",
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
