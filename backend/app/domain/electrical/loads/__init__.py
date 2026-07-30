"""
Electrical load and demand calculation domain.
KESE-S2-M1
"""

from app.domain.electrical.loads.engine import (
    calculate_load,
    calculate_load_group,
)
from app.domain.electrical.loads.models import (
    LoadGroupInput,
    LoadInput,
    LoadScenario,
    PhaseSystem,
    PowerBasis,
)
from app.domain.electrical.loads.results import (
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