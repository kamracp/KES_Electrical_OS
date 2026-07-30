"""
Electrical load and demand calculation domain.
KESE-S2-M1
"""

from kes_electrical_core.loads.engine import (
    calculate_load,
    calculate_load_group,
)
from kes_electrical_core.loads.models import (
    LoadGroupInput,
    LoadInput,
    LoadScenario,
    PhaseSystem,
    PowerBasis,
)
from kes_electrical_core.loads.results import (
    CalculationStatus,
    CalculationWarning,
    LoadCalculationResult,
    LoadGroupCalculationResult,
    LoadWarningCode,
)

__all__ = [
    "CalculationStatus",
    "CalculationWarning",
    "LoadCalculationResult",
    "LoadGroupCalculationResult",
    "LoadGroupInput",
    "LoadInput",
    "LoadScenario",
    "LoadWarningCode",
    "PhaseSystem",
    "PowerBasis",
    "calculate_load",
    "calculate_load_group",
]