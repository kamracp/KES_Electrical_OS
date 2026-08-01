"""
Electrical transformer, generator, and UPS source-sizing domain.

KESE-S2-M4 / KESE-S2-M6 / KESE-S2-M7
"""

from app.domain.electrical.sources.engine import (
    calculate_transformer_sizing,
)
from app.domain.electrical.sources.generator_engine import (
    calculate_generator_sizing,
)
from app.domain.electrical.sources.generator_models import (
    GeneratorDutyClass,
    GeneratorRedundancyMode,
    GeneratorSizingInput,
)
from app.domain.electrical.sources.generator_results import (
    GeneratorSizingResult,
    GeneratorSizingStatus,
    GeneratorSizingWarning,
    GeneratorSizingWarningCode,
)
from app.domain.electrical.sources.models import (
    TransformerRedundancyMode,
    TransformerSizingInput,
)
from app.domain.electrical.sources.results import (
    TransformerSizingResult,
    TransformerSizingStatus,
    TransformerSizingWarning,
    TransformerSizingWarningCode,
)
from app.domain.electrical.sources.ups_engine import (
    calculate_ups_sizing,
)
from app.domain.electrical.sources.ups_models import (
    UPSBatteryTechnology,
    UPSPhaseConfiguration,
    UPSRedundancyMode,
    UPSSizingInput,
    UPSTopology,
)
from app.domain.electrical.sources.ups_results import (
    UPSSizingResult,
    UPSSizingStatus,
)
from app.domain.electrical.sources.pv_engine import (
    calculate_pv_sizing,
)
from app.domain.electrical.sources.pv_models import (
    PVBatteryConfiguration,
    PVInverterRedundancyMode,
    PVPhaseConfiguration,
    PVSizingInput,
    PVSystemType,
)
from app.domain.electrical.sources.pv_results import (
    PVSizingResult,
    PVSizingStatus,
    PVSizingWarning,
    PVSizingWarningCode,
)



__all__ = [
    "GeneratorDutyClass",
    "GeneratorRedundancyMode",
    "GeneratorSizingInput",
    "GeneratorSizingResult",
    "GeneratorSizingStatus",
    "GeneratorSizingWarning",
    "GeneratorSizingWarningCode",
    "TransformerRedundancyMode",
    "TransformerSizingInput",
    "TransformerSizingResult",
    "TransformerSizingStatus",
    "TransformerSizingWarning",
    "TransformerSizingWarningCode",
    "UPSBatteryTechnology",
    "UPSPhaseConfiguration",
    "UPSRedundancyMode",
    "UPSSizingInput",
    "UPSSizingResult",
    "UPSSizingStatus",
    "UPSTopology",
    "calculate_generator_sizing",
    "calculate_transformer_sizing",
    "calculate_ups_sizing",
]
"PVBatteryConfiguration",
"PVInverterRedundancyMode",
"PVPhaseConfiguration",
"PVSizingInput",
"PVSizingResult",
"PVSizingStatus",
"PVSizingWarning",
"PVSizingWarningCode",
"PVSystemType",
"calculate_pv_sizing",
