"""
Symmetrical-sequence network reduction for short-circuit studies.
KESE-S2-M15
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from app.domain.electrical.fault.fault_models import (
    FaultBranchInput,
    FaultBusInput,
    FaultSourceInput,
    NeutralEarthingMode,
    SequenceImpedanceInput,
    ShortCircuitStudyInput,
    SourceRepresentation,
)
from app.domain.electrical.fault.fault_results import FaultSequence


@dataclass(frozen=True, slots=True)
class SequenceNetworkReduction:
    """Driving-point impedance and traceability for one sequence network."""

    sequence: FaultSequence
    available: bool
    resistance_ohm: Decimal | None
    reactance_ohm: Decimal | None
    connected_bus_codes: tuple[str, ...]
    path_reference_codes: tuple[str, ...]
    blocking_reference_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _DecimalComplex:
    """Minimal exact-decimal complex value for nodal-admittance reduction."""

    real: Decimal
    imag: Decimal

    @classmethod
    def zero(cls) -> "_DecimalComplex":
        return cls(Decimal("0"), Decimal("0"))

    @classmethod
    def from_impedance(cls, value: SequenceImpedanceInput) -> "_DecimalComplex":
        return cls(value.resistance_ohm, value.reactance_ohm)

    def __add__(self, other: "_DecimalComplex") -> "_DecimalComplex":
        return _DecimalComplex(
            self.real + other.real,
            self.imag + other.imag,
        )

    def __sub__(self, other: "_DecimalComplex") -> "_DecimalComplex":
        return _DecimalComplex(
            self.real - other.real,
            self.imag - other.imag,
        )

    def __mul__(self, other: "_DecimalComplex") -> "_DecimalComplex":
        return _DecimalComplex(
            self.real * other.real - self.imag * other.imag,
            self.real * other.imag + self.imag * other.real,
        )

    def __truediv__(self, other: "_DecimalComplex") -> "_DecimalComplex":
        return self * other.reciprocal()

    def scale(self, factor: Decimal) -> "_DecimalComplex":
        return _DecimalComplex(
            self.real * factor,
            self.imag * factor,
        )

    def reciprocal(self) -> "_DecimalComplex":
        denominator = self.abs_squared()
        if denominator == Decimal("0"):
            raise ZeroDivisionError("cannot invert zero complex impedance")

        return _DecimalComplex(
            self.real / denominator,
            -self.imag / denominator,
        )

    def abs_squared(self) -> Decimal:
        return self.real * self.real + self.imag * self.imag

    def is_zero(self) -> bool:
        return self.real == Decimal("0") and self.imag == Decimal("0")


def _sequence_impedance(
    record: FaultBranchInput | FaultSourceInput,
    sequence: FaultSequence,
) -> SequenceImpedanceInput | None:
    if sequence is FaultSequence.POSITIVE:
        return record.positive_sequence_impedance
    if sequence is FaultSequence.NEGATIVE:
        return record.negative_sequence_impedance
    return record.zero_sequence_impedance


def _neutral_impedance(
    bus: FaultBusInput,
) -> _DecimalComplex | None:
    if bus.neutral_earthing_mode is NeutralEarthingMode.ISOLATED:
        return None

    return _DecimalComplex(
        bus.neutral_resistance_ohm,
        bus.neutral_reactance_ohm,
    )


def _source_shunt_admittance(
    source: FaultSourceInput,
    bus: FaultBusInput,
    sequence: FaultSequence,
) -> _DecimalComplex | None:
    if not source.in_service:
        return None

    if source.representation is not SourceRepresentation.VOLTAGE_BEHIND_IMPEDANCE:
        return None

    impedance_input = _sequence_impedance(
        source,
        sequence,
    )
    if impedance_input is None:
        return None

    impedance = _DecimalComplex.from_impedance(impedance_input)

    if sequence is FaultSequence.ZERO:
        neutral_impedance = _neutral_impedance(bus)

        if neutral_impedance is None:
            return None

        impedance = impedance + neutral_impedance.scale(Decimal("3"))

    return impedance.reciprocal().scale(source.contribution_factor)


def _branch_admittance(
    branch: FaultBranchInput,
    sequence: FaultSequence,
) -> _DecimalComplex | None:
    if not branch.in_service:
        return None

    impedance_input = _sequence_impedance(
        branch,
        sequence,
    )
    if impedance_input is None:
        return None

    return (
        _DecimalComplex.from_impedance(impedance_input)
        .reciprocal()
        .scale(Decimal(branch.parallel_circuits))
    )


def _connected_component(
    study: ShortCircuitStudyInput,
    sequence: FaultSequence,
) -> tuple[set[str], tuple[str, ...]]:
    adjacency: dict[str, set[str]] = {bus.code: set() for bus in study.buses}

    eligible_branch_codes: set[str] = set()

    for branch in study.branches:
        if (
            _branch_admittance(
                branch,
                sequence,
            )
            is None
        ):
            continue

        adjacency[branch.from_bus_code].add(branch.to_bus_code)

        adjacency[branch.to_bus_code].add(branch.from_bus_code)

        eligible_branch_codes.add(branch.code)

    connected_bus_codes = {study.fault.bus_code}

    pending_bus_codes = [study.fault.bus_code]

    while pending_bus_codes:
        current_bus_code = pending_bus_codes.pop()

        for next_bus_code in adjacency[current_bus_code]:
            if next_bus_code in connected_bus_codes:
                continue

            connected_bus_codes.add(next_bus_code)

            pending_bus_codes.append(next_bus_code)

    component_branch_codes = tuple(
        sorted(
            branch.code
            for branch in study.branches
            if (branch.code in eligible_branch_codes)
            and (branch.from_bus_code in connected_bus_codes)
            and (branch.to_bus_code in connected_bus_codes)
        )
    )

    return (
        connected_bus_codes,
        component_branch_codes,
    )


def _blocking_reference_codes(
    study: ShortCircuitStudyInput,
    sequence: FaultSequence,
) -> tuple[str, ...]:
    bus_by_code = {bus.code: bus for bus in study.buses}

    blocking_reference_codes: set[str] = set()

    for branch in study.branches:
        if (
            branch.in_service
            and _sequence_impedance(
                branch,
                sequence,
            )
            is None
        ):
            blocking_reference_codes.add(branch.code)

    for source in study.sources:
        if not source.in_service:
            continue

        if source.representation is SourceRepresentation.CURRENT_INJECTION:
            continue

        if (
            _sequence_impedance(
                source,
                sequence,
            )
            is None
        ):
            blocking_reference_codes.add(source.code)
            continue

        if (
            sequence is FaultSequence.ZERO
            and _neutral_impedance(bus_by_code[source.bus_code]) is None
        ):
            blocking_reference_codes.add(source.code)

    if not blocking_reference_codes:
        blocking_reference_codes.add(study.fault.bus_code)

    return tuple(sorted(blocking_reference_codes))


def _empty_matrix(
    size: int,
) -> list[list[_DecimalComplex]]:
    return [[_DecimalComplex.zero() for _ in range(size)] for _ in range(size)]


def _solve_linear_system(
    matrix: list[list[_DecimalComplex]],
    vector: list[_DecimalComplex],
) -> list[_DecimalComplex]:
    size = len(vector)

    coefficients = [row[:] for row in matrix]

    right_hand_side = vector[:]

    for column in range(size):
        pivot_row = max(
            range(
                column,
                size,
            ),
            key=lambda row: coefficients[row][column].abs_squared(),
        )

        if coefficients[pivot_row][column].is_zero():
            raise ValueError("sequence nodal-admittance matrix is singular")

        if pivot_row != column:
            (
                coefficients[column],
                coefficients[pivot_row],
            ) = (
                coefficients[pivot_row],
                coefficients[column],
            )

            (
                right_hand_side[column],
                right_hand_side[pivot_row],
            ) = (
                right_hand_side[pivot_row],
                right_hand_side[column],
            )

        pivot = coefficients[column][column]

        for row in range(
            column + 1,
            size,
        ):
            if coefficients[row][column].is_zero():
                continue

            factor = coefficients[row][column] / pivot

            for index in range(
                column,
                size,
            ):
                coefficients[row][index] = (
                    coefficients[row][index] - factor * coefficients[column][index]
                )

            right_hand_side[row] = right_hand_side[row] - factor * right_hand_side[column]

    solution = [_DecimalComplex.zero() for _ in range(size)]

    for row in range(
        size - 1,
        -1,
        -1,
    ):
        remainder = right_hand_side[row]

        for column in range(
            row + 1,
            size,
        ):
            remainder = remainder - coefficients[row][column] * solution[column]

        solution[row] = remainder / coefficients[row][row]

    return solution


def reduce_sequence_network(
    study: ShortCircuitStudyInput,
    sequence: FaultSequence,
) -> SequenceNetworkReduction:
    """
    Reduce one passive symmetrical-sequence network to the fault bus.

    Voltage-behind-impedance sources are suppressed to their sequence
    impedances. Current-injection sources are excluded from passive
    reduction and are handled later by the fault-current engine.
    """

    if not isinstance(
        study,
        ShortCircuitStudyInput,
    ):
        raise TypeError("study must be a ShortCircuitStudyInput record")

    if not isinstance(
        sequence,
        FaultSequence,
    ):
        raise TypeError("sequence must be a FaultSequence value")

    with localcontext() as context:
        context.prec = 50

        (
            connected_bus_codes,
            component_branch_codes,
        ) = _connected_component(
            study,
            sequence,
        )

        ordered_bus_codes = tuple(sorted(connected_bus_codes))

        bus_index = {bus_code: index for index, bus_code in enumerate(ordered_bus_codes)}

        bus_by_code = {bus.code: bus for bus in study.buses}

        matrix = _empty_matrix(len(ordered_bus_codes))

        for branch in study.branches:
            if (
                branch.from_bus_code not in connected_bus_codes
                or branch.to_bus_code not in connected_bus_codes
            ):
                continue

            admittance = _branch_admittance(
                branch,
                sequence,
            )

            if admittance is None:
                continue

            from_index = bus_index[branch.from_bus_code]

            to_index = bus_index[branch.to_bus_code]

            matrix[from_index][from_index] = matrix[from_index][from_index] + admittance

            matrix[to_index][to_index] = matrix[to_index][to_index] + admittance

            matrix[from_index][to_index] = matrix[from_index][to_index] - admittance

            matrix[to_index][from_index] = matrix[to_index][from_index] - admittance

        source_codes: list[str] = []

        for source in study.sources:
            if source.bus_code not in connected_bus_codes:
                continue

            admittance = _source_shunt_admittance(
                source,
                bus_by_code[source.bus_code],
                sequence,
            )

            if admittance is None:
                continue

            source_index = bus_index[source.bus_code]

            matrix[source_index][source_index] = matrix[source_index][source_index] + admittance

            source_codes.append(source.code)

        if not source_codes:
            return SequenceNetworkReduction(
                sequence=sequence,
                available=False,
                resistance_ohm=None,
                reactance_ohm=None,
                connected_bus_codes=(ordered_bus_codes),
                path_reference_codes=(),
                blocking_reference_codes=(
                    _blocking_reference_codes(
                        study,
                        sequence,
                    )
                ),
            )

        injection = [_DecimalComplex.zero() for _ in ordered_bus_codes]

        injection[bus_index[study.fault.bus_code]] = _DecimalComplex(
            Decimal("1"),
            Decimal("0"),
        )

        try:
            voltage_solution = _solve_linear_system(
                matrix,
                injection,
            )
        except ValueError:
            return SequenceNetworkReduction(
                sequence=sequence,
                available=False,
                resistance_ohm=None,
                reactance_ohm=None,
                connected_bus_codes=(ordered_bus_codes),
                path_reference_codes=(),
                blocking_reference_codes=(
                    _blocking_reference_codes(
                        study,
                        sequence,
                    )
                ),
            )

        equivalent_impedance = voltage_solution[bus_index[study.fault.bus_code]]

        if (
            equivalent_impedance.real < Decimal("0")
            or equivalent_impedance.imag < Decimal("0")
            or equivalent_impedance.is_zero()
        ):
            raise ValueError("reduced sequence impedance must be non-negative and non-zero")

        path_reference_codes = tuple(sorted(set(component_branch_codes) | set(source_codes)))

        return SequenceNetworkReduction(
            sequence=sequence,
            available=True,
            resistance_ohm=(equivalent_impedance.real),
            reactance_ohm=(equivalent_impedance.imag),
            connected_bus_codes=(ordered_bus_codes),
            path_reference_codes=(path_reference_codes),
            blocking_reference_codes=(),
        )


__all__ = [
    "SequenceNetworkReduction",
    "reduce_sequence_network",
]
