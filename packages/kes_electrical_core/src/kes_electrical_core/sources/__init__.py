"""
Electrical transformer and generator source-sizing domain.
KESE-S2-M4 / KESE-S2-M6
"""

from kes_electrical_core.sources.engine import (
    calculate_transformer_sizing,
)
from kes_electrical_core.sources.generator_engine import (
    calculate_generator_sizing,
)
from kes_electrical_core.sources.generator_models import (
    GeneratorDutyClass,
    GeneratorRedundancyMode,
    GeneratorSizingInput,
)
from kes_electrical_core.sources.generator_results import (
    GeneratorSizingResult,
    GeneratorSizingStatus,
    GeneratorSizingWarning,
    GeneratorSizingWarningCode,
)
from kes_electrical_core.sources.models import (
    TransformerRedundancyMode,
    TransformerSizingInput,
)
from kes_electrical_core.sources.results import (
    TransformerSizingResult,
    TransformerSizingStatus,
    TransformerSizingWarning,
    TransformerSizingWarningCode,
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
    "calculate_generator_sizing",
    "calculate_transformer_sizing",
]
