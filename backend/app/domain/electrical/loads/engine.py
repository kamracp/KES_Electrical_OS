"""
Pure domain engine for electrical load and demand calculations.
KESE-S2-M1
"""

from dataclasses import dataclass
from decimal import (
    ROUND_HALF_UP,
    Decimal,
    localcontext,
)

from app.domain.electrical.loads.models import (
    LoadGroupInput,
    LoadInput,
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

POWER_QUANTUM = Decimal("0.0001")
CURRENT_QUANTUM = Decimal("0.0001")

LOW_POWER_FACTOR_LIMIT = Decimal("0.80")
LOW_EFFICIENCY_LIMIT = Decimal("0.80")


@dataclass(frozen=True, slots=True)
class _RawLoadValues:
    """Unrounded internal values for one load calculation."""

    connected_power_kw: Decimal
    utilized_power_kw: Decimal
    demand_power_kw: Decimal
    apparent_power_kva: Decimal
    reactive_power_kvar: Decimal
    design_current_a: Decimal


def _round_power(value: Decimal) -> Decimal:
    """Round a power value to four decimal places."""

    return value.quantize(
        POWER_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _round_current(value: Decimal) -> Decimal:
    """Round an electrical current to four decimal places."""

    return value.quantize(
        CURRENT_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def _square_root(value: Decimal) -> Decimal:
    """Calculate a high-precision Decimal square root."""

    if value < Decimal("0"):
        raise ValueError(
            "square root input must not be negative"
        )

    with localcontext() as context:
        context.prec = 50
        return value.sqrt()


def _calculate_connected_power(
    load: LoadInput,
) -> Decimal:
    """
    Calculate total connected electrical input power.

    Mechanical-output ratings are divided by efficiency to determine
    the corresponding electrical input requirement.
    """

    quantity = Decimal(load.quantity)

    if load.power_basis is PowerBasis.MECHANICAL_OUTPUT:
        per_unit_input_kw = (
            load.rated_power_kw
            / load.efficiency
        )
    else:
        per_unit_input_kw = load.rated_power_kw

    return per_unit_input_kw * quantity


def _calculate_raw_load(
    load: LoadInput,
) -> _RawLoadValues:
    """Calculate unrounded electrical values for one load."""

    with localcontext() as context:
        context.prec = 50

        connected_power_kw = (
            _calculate_connected_power(load)
        )

        utilized_power_kw = (
            connected_power_kw
            * load.utilization_factor
        )

        demand_power_kw = (
            utilized_power_kw
            * load.demand_factor
        )

        if load.phase_system is PhaseSystem.DC:
            apparent_power_kva = demand_power_kw
            reactive_power_kvar = Decimal("0")

            design_current_a = (
                demand_power_kw
                * Decimal("1000")
                / load.voltage_v
            )
        else:
            apparent_power_kva = (
                demand_power_kw
                / load.power_factor
            )

            reactive_squared = (
                apparent_power_kva
                * apparent_power_kva
                - demand_power_kw
                * demand_power_kw
            )

            reactive_power_kvar = _square_root(
                reactive_squared
            )

            if load.phase_system is PhaseSystem.SINGLE_PHASE:
                design_current_a = (
                    apparent_power_kva
                    * Decimal("1000")
                    / load.voltage_v
                )
            else:
                design_current_a = (
                    apparent_power_kva
                    * Decimal("1000")
                    / (
                        _square_root(Decimal("3"))
                        * load.voltage_v
                    )
                )

    return _RawLoadValues(
        connected_power_kw=connected_power_kw,
        utilized_power_kw=utilized_power_kw,
        demand_power_kw=demand_power_kw,
        apparent_power_kva=apparent_power_kva,
        reactive_power_kvar=reactive_power_kvar,
        design_current_a=design_current_a,
    )


def _build_load_warnings(
    load: LoadInput,
    raw_values: _RawLoadValues,
) -> tuple[CalculationWarning, ...]:
    """Create controlled warnings for one load calculation."""

    warnings: list[CalculationWarning] = []

    if raw_values.demand_power_kw == Decimal("0"):
        warnings.append(
            CalculationWarning(
                code=LoadWarningCode.ZERO_DEMAND,
                message=(
                    "Calculated demand is zero because the "
                    "utilization factor or demand factor is zero."
                ),
            )
        )

    if (
        load.phase_system is not PhaseSystem.DC
        and load.power_factor < LOW_POWER_FACTOR_LIMIT
    ):
        warnings.append(
            CalculationWarning(
                code=LoadWarningCode.LOW_POWER_FACTOR,
                message=(
                    "Power factor is below the preferred "
                    "limit of 0.80."
                ),
            )
        )

    if (
        load.power_basis is PowerBasis.MECHANICAL_OUTPUT
        and load.efficiency < LOW_EFFICIENCY_LIMIT
    ):
        warnings.append(
            CalculationWarning(
                code=LoadWarningCode.LOW_EFFICIENCY,
                message=(
                    "Equipment efficiency is below the "
                    "preferred limit of 0.80."
                ),
            )
        )

    return tuple(warnings)


def _build_load_result(
    load: LoadInput,
    raw_values: _RawLoadValues,
) -> LoadCalculationResult:
    """Convert raw values into a validated calculation result."""

    warnings = _build_load_warnings(
        load,
        raw_values,
    )

    status = (
        CalculationStatus.WARNING
        if warnings
        else CalculationStatus.VALID
    )

    return LoadCalculationResult(
        load_code=load.code,
        load_name=load.name,
        scenario=load.scenario,
        phase_system=load.phase_system,
        connected_power_kw=_round_power(
            raw_values.connected_power_kw
        ),
        utilized_power_kw=_round_power(
            raw_values.utilized_power_kw
        ),
        demand_power_kw=_round_power(
            raw_values.demand_power_kw
        ),
        apparent_power_kva=_round_power(
            raw_values.apparent_power_kva
        ),
        reactive_power_kvar=_round_power(
            raw_values.reactive_power_kvar
        ),
        design_current_a=_round_current(
            raw_values.design_current_a
        ),
        status=status,
        warnings=warnings,
    )


def calculate_load(
    load: LoadInput,
) -> LoadCalculationResult:
    """
    Calculate connected load, demand, power components and current.

    This function is pure and does not access a database, API,
    environment configuration, or external service.
    """

    if not isinstance(load, LoadInput):
        raise TypeError(
            "load must be a LoadInput record"
        )

    raw_values = _calculate_raw_load(load)

    return _build_load_result(
        load,
        raw_values,
    )


def calculate_load_group(
    group: LoadGroupInput,
) -> LoadGroupCalculationResult:
    """
    Calculate and aggregate an electrical load group.

    Group coincidence is applied uniformly to active and reactive
    demand after individual load calculations.
    """

    if not isinstance(group, LoadGroupInput):
        raise TypeError(
            "group must be a LoadGroupInput record"
        )

    raw_calculations = tuple(
        (
            load,
            _calculate_raw_load(load),
        )
        for load in group.loads
    )

    load_results = tuple(
        _build_load_result(
            load,
            raw_values,
        )
        for load, raw_values in raw_calculations
    )

    connected_power_kw = sum(
        (
            raw_values.connected_power_kw
            for _, raw_values in raw_calculations
        ),
        Decimal("0"),
    )

    pre_coincidence_demand_kw = sum(
        (
            raw_values.demand_power_kw
            for _, raw_values in raw_calculations
        ),
        Decimal("0"),
    )

    pre_coincidence_reactive_kvar = sum(
        (
            raw_values.reactive_power_kvar
            for _, raw_values in raw_calculations
        ),
        Decimal("0"),
    )

    demand_power_kw = (
        pre_coincidence_demand_kw
        * group.coincidence_factor
    )

    reactive_power_kvar = (
        pre_coincidence_reactive_kvar
        * group.coincidence_factor
    )

    apparent_power_kva = _square_root(
        demand_power_kw * demand_power_kw
        + reactive_power_kvar * reactive_power_kvar
    )

    group_warnings = tuple(
        CalculationWarning(
            code=warning.code,
            message=(
                f"{load_result.load_code}: "
                f"{warning.message}"
            ),
        )
        for load_result in load_results
        for warning in load_result.warnings
    )

    status = (
        CalculationStatus.WARNING
        if group_warnings
        else CalculationStatus.VALID
    )

    return LoadGroupCalculationResult(
        group_code=group.code,
        group_name=group.name,
        coincidence_factor=group.coincidence_factor,
        connected_power_kw=_round_power(
            connected_power_kw
        ),
        pre_coincidence_demand_kw=_round_power(
            pre_coincidence_demand_kw
        ),
        demand_power_kw=_round_power(
            demand_power_kw
        ),
        apparent_power_kva=_round_power(
            apparent_power_kva
        ),
        reactive_power_kvar=_round_power(
            reactive_power_kvar
        ),
        load_results=load_results,
        status=status,
        warnings=group_warnings,
    )


__all__ = [
    "calculate_load",
    "calculate_load_group",
]