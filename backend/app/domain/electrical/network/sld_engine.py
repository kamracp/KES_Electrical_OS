"""
Deterministic source-integration and single-line-diagram evaluation engine.
KESE-S2-M14
"""

from collections import deque

from app.domain.electrical.network.sld_models import (
    SLDNetworkInput,
    SLDNodeType,
    SLDOperatingStateInput,
    SynchronizationPolicy,
)
from app.domain.electrical.network.sld_results import (
    SLDCheckStatus,
    SLDConnectionStateResult,
    SLDEngineeringWarning,
    SLDInterlockResult,
    SLDNetworkResult,
    SLDNodeStateResult,
    SLDOperatingStateResult,
    SLDResultStatus,
    SLDSourceStateResult,
    SLDWarningCode,
    SLDWarningSeverity,
)
from app.domain.electrical.sources.common import normalize_required_text

_SOURCE_NODE_TYPES = {
    SLDNodeType.UTILITY_GRID,
    SLDNodeType.GENERATOR,
    SLDNodeType.SOLAR_PV,
    SLDNodeType.UPS,
}


class SLDEngine:
    """Evaluate source hierarchy and energized topology for every SLD state."""

    @classmethod
    def evaluate(cls, network: SLDNetworkInput) -> SLDNetworkResult:
        """Evaluate every operating state defined by an SLD network."""

        cls._require_network(network)
        state_results = tuple(
            cls.evaluate_operating_state(network, state.code) for state in network.operating_states
        )

        status = SLDResultStatus.COMPLIANT
        if any(result.status is SLDResultStatus.NON_COMPLIANT for result in state_results):
            status = SLDResultStatus.NON_COMPLIANT
        elif any(result.status is SLDResultStatus.WARNING for result in state_results):
            status = SLDResultStatus.WARNING

        return SLDNetworkResult(
            network_code=network.code,
            status=status,
            operating_state_results=state_results,
            standard_reference=network.standard_reference,
        )

    @classmethod
    def evaluate_operating_state(
        cls,
        network: SLDNetworkInput,
        state_code: str,
    ) -> SLDOperatingStateResult:
        """Evaluate one named operating state of an SLD network."""

        cls._require_network(network)
        normalized_state_code = normalize_required_text("state_code", state_code)
        state = next(
            (
                candidate
                for candidate in network.operating_states
                if candidate.code == normalized_state_code
            ),
            None,
        )
        if state is None:
            raise ValueError(f"unknown operating state code: {normalized_state_code}")

        return cls._evaluate_state(network, state)

    @classmethod
    def _evaluate_state(
        cls,
        network: SLDNetworkInput,
        state: SLDOperatingStateInput,
    ) -> SLDOperatingStateResult:
        node_by_code = {node.code: node for node in network.nodes}
        isolated_codes = set(state.isolated_node_codes)
        closed_codes = set(state.closed_connection_codes)
        available_node_codes = {
            node.code for node in network.nodes if node.enabled and node.code not in isolated_codes
        }
        adjacency = cls._build_adjacency(
            network,
            closed_codes=closed_codes,
            available_node_codes=available_node_codes,
        )

        source_nodes = tuple(
            sorted(
                (node for node in network.nodes if node.node_type in _SOURCE_NODE_TYPES),
                key=lambda node: (node.source_priority or 0, node.code),
            )
        )
        active_source_codes = set(state.active_source_codes)
        reachability_by_source: dict[str, frozenset[str]] = {}
        warnings: list[SLDEngineeringWarning] = []

        for source in source_nodes:
            if source.code not in active_source_codes:
                reachability_by_source[source.code] = frozenset()
                continue

            if source.code not in available_node_codes:
                reachability_by_source[source.code] = frozenset()
                cls._append_warning(
                    warnings,
                    code=SLDWarningCode.ACTIVE_SOURCE_DISABLED,
                    severity=SLDWarningSeverity.ERROR,
                    message=f"Active source {source.code} is disabled or isolated",
                    reference_code=source.code,
                )
                continue

            reachability_by_source[source.code] = cls._reachable_nodes(
                source.code,
                adjacency,
            )

        active_energized_sources = tuple(
            source
            for source in source_nodes
            if source.code in active_source_codes and reachability_by_source[source.code]
        )
        primary_source_code = active_energized_sources[0].code if active_energized_sources else None

        if primary_source_code is None:
            cls._append_warning(
                warnings,
                code=SLDWarningCode.NO_PRIMARY_SOURCE,
                severity=SLDWarningSeverity.ERROR,
                message=f"Operating state {state.code} has no energized primary source",
                reference_code=state.code,
            )
        else:
            requested_active_sources = tuple(
                source for source in source_nodes if source.code in active_source_codes
            )
            requested_primary = requested_active_sources[0]
            selected_primary = node_by_code[primary_source_code]
            if selected_primary.source_priority != requested_primary.source_priority:
                cls._append_warning(
                    warnings,
                    code=SLDWarningCode.SOURCE_PRIORITY_BYPASSED,
                    severity=SLDWarningSeverity.WARNING,
                    message=(
                        f"Source {primary_source_code} is selected while higher-priority "
                        f"source {requested_primary.code} is unavailable"
                    ),
                    reference_code=primary_source_code,
                )

        supplying_sources_by_node = {
            node.code: tuple(
                source.code
                for source in source_nodes
                if node.code in reachability_by_source[source.code]
            )
            for node in network.nodes
        }

        source_results = tuple(
            SLDSourceStateResult(
                source_code=source.code,
                priority=source.source_priority or 1,
                active=source.code in active_source_codes,
                primary=source.code == primary_source_code,
                supplied_node_codes=tuple(
                    node.code
                    for node in network.nodes
                    if node.code in reachability_by_source[source.code]
                ),
            )
            for source in source_nodes
        )

        node_results = tuple(
            SLDNodeStateResult(
                node_code=node.code,
                node_type=node.node_type,
                enabled=node.enabled,
                energized=bool(supplying_sources_by_node[node.code]),
                isolated=node.code in isolated_codes,
                supplying_source_codes=supplying_sources_by_node[node.code],
            )
            for node in network.nodes
        )
        node_result_by_code = {result.node_code: result for result in node_results}

        cls._add_node_warnings(
            network,
            state,
            node_result_by_code,
            warnings,
        )

        connection_results: list[SLDConnectionStateResult] = []
        for connection in network.connections:
            closed = connection.code in closed_codes
            from_result = node_result_by_code[connection.from_node_code]
            to_result = node_result_by_code[connection.to_node_code]
            energized = closed and (from_result.energized or to_result.energized)
            connection_results.append(
                SLDConnectionStateResult(
                    connection_code=connection.code,
                    closed=closed,
                    energized=energized,
                    from_node_energized=from_result.energized,
                    to_node_energized=to_result.energized,
                )
            )

            if closed and not energized:
                cls._append_warning(
                    warnings,
                    code=SLDWarningCode.CLOSED_CONNECTION_UNENERGIZED,
                    severity=SLDWarningSeverity.WARNING,
                    message=f"Closed connection {connection.code} is not energized",
                    reference_code=connection.code,
                )

            from_sources = set(from_result.supplying_source_codes)
            to_sources = set(to_result.supplying_source_codes)
            if closed and not connection.bidirectional_power_flow and to_sources - from_sources:
                cls._append_warning(
                    warnings,
                    code=SLDWarningCode.REVERSE_POWER_FLOW_BLOCKED,
                    severity=SLDWarningSeverity.WARNING,
                    message=(
                        f"Connection {connection.code} is exposed to blocked reverse "
                        "source reachability"
                    ),
                    reference_code=connection.code,
                )

            if (
                closed
                and energized
                and connection.synchronization_policy is SynchronizationPolicy.REQUIRED
            ):
                cls._append_warning(
                    warnings,
                    code=SLDWarningCode.SYNCHRONIZATION_REQUIRED,
                    severity=SLDWarningSeverity.WARNING,
                    message=(
                        f"Connection {connection.code} requires verified synchronization "
                        "before closure"
                    ),
                    reference_code=connection.code,
                )

        parallel_node_codes = tuple(
            node_code
            for node_code, source_codes in supplying_sources_by_node.items()
            if len(source_codes) > 1
        )
        if parallel_node_codes:
            cls._append_warning(
                warnings,
                code=SLDWarningCode.MULTIPLE_ACTIVE_SOURCES,
                severity=SLDWarningSeverity.WARNING,
                message=(
                    "Multiple active sources operate in parallel at nodes: "
                    + ", ".join(parallel_node_codes)
                ),
                reference_code=state.code,
            )

        interlock_results: list[SLDInterlockResult] = []
        for interlock in network.interlocks:
            closed_interlocked_codes = tuple(
                code for code in interlock.connection_codes if code in closed_codes
            )
            interlock_status = (
                SLDCheckStatus.PASS
                if len(closed_interlocked_codes) <= interlock.maximum_simultaneously_closed
                else SLDCheckStatus.FAIL
            )
            interlock_results.append(
                SLDInterlockResult(
                    interlock_code=interlock.code,
                    closed_connection_codes=closed_interlocked_codes,
                    maximum_simultaneously_closed=(interlock.maximum_simultaneously_closed),
                    status=interlock_status,
                )
            )
            if interlock_status is SLDCheckStatus.FAIL:
                cls._append_warning(
                    warnings,
                    code=SLDWarningCode.INTERLOCK_VIOLATION,
                    severity=SLDWarningSeverity.ERROR,
                    message=f"Operating state violates interlock {interlock.code}",
                    reference_code=interlock.code,
                )

        status = cls._result_status(warnings, tuple(interlock_results))
        return SLDOperatingStateResult(
            network_code=network.code,
            state_code=state.code,
            mode=state.mode,
            status=status,
            primary_source_code=primary_source_code,
            source_results=source_results,
            node_results=node_results,
            connection_results=tuple(connection_results),
            interlock_results=tuple(interlock_results),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _require_network(network: SLDNetworkInput) -> None:
        if not isinstance(network, SLDNetworkInput):
            raise TypeError("network must be an SLDNetworkInput record")

    @staticmethod
    def _build_adjacency(
        network: SLDNetworkInput,
        *,
        closed_codes: set[str],
        available_node_codes: set[str],
    ) -> dict[str, tuple[str, ...]]:
        adjacency: dict[str, list[str]] = {node_code: [] for node_code in available_node_codes}
        for connection in network.connections:
            if connection.code not in closed_codes:
                continue
            if (
                connection.from_node_code not in available_node_codes
                or connection.to_node_code not in available_node_codes
            ):
                continue

            adjacency[connection.from_node_code].append(connection.to_node_code)
            if connection.bidirectional_power_flow:
                adjacency[connection.to_node_code].append(connection.from_node_code)

        return {
            node_code: tuple(connected_codes) for node_code, connected_codes in adjacency.items()
        }

    @staticmethod
    def _reachable_nodes(
        source_code: str,
        adjacency: dict[str, tuple[str, ...]],
    ) -> frozenset[str]:
        visited: set[str] = set()
        pending = deque((source_code,))
        while pending:
            node_code = pending.popleft()
            if node_code in visited:
                continue
            visited.add(node_code)
            pending.extend(
                connected_code
                for connected_code in adjacency[node_code]
                if connected_code not in visited
            )
        return frozenset(visited)

    @classmethod
    def _add_node_warnings(
        cls,
        network: SLDNetworkInput,
        state: SLDOperatingStateInput,
        node_result_by_code: dict[str, SLDNodeStateResult],
        warnings: list[SLDEngineeringWarning],
    ) -> None:
        isolated_codes = set(state.isolated_node_codes)
        active_source_codes = set(state.active_source_codes)
        for node in network.nodes:
            result = node_result_by_code[node.code]
            if (
                not node.enabled
                or not node.normally_energized
                or node.code in isolated_codes
                or result.energized
            ):
                continue

            if node.node_type is SLDNodeType.FINAL_LOAD:
                cls._append_warning(
                    warnings,
                    code=SLDWarningCode.FINAL_LOAD_UNSUPPLIED,
                    severity=SLDWarningSeverity.ERROR,
                    message=f"Normally energized final load {node.code} is not supplied",
                    reference_code=node.code,
                )
            elif node.node_type in _SOURCE_NODE_TYPES:
                if node.code in active_source_codes:
                    continue
            else:
                cls._append_warning(
                    warnings,
                    code=SLDWarningCode.ENABLED_NODE_UNENERGIZED,
                    severity=SLDWarningSeverity.WARNING,
                    message=f"Normally energized node {node.code} is not energized",
                    reference_code=node.code,
                )

    @staticmethod
    def _append_warning(
        warnings: list[SLDEngineeringWarning],
        *,
        code: SLDWarningCode,
        severity: SLDWarningSeverity,
        message: str,
        reference_code: str,
    ) -> None:
        if any(
            warning.code is code and warning.reference_code == reference_code
            for warning in warnings
        ):
            return
        warnings.append(
            SLDEngineeringWarning(
                code=code,
                severity=severity,
                message=message,
                reference_code=reference_code,
            )
        )

    @staticmethod
    def _result_status(
        warnings: list[SLDEngineeringWarning],
        interlock_results: tuple[SLDInterlockResult, ...],
    ) -> SLDResultStatus:
        if any(warning.severity is SLDWarningSeverity.ERROR for warning in warnings) or any(
            result.status is SLDCheckStatus.FAIL for result in interlock_results
        ):
            return SLDResultStatus.NON_COMPLIANT
        if warnings:
            return SLDResultStatus.WARNING
        return SLDResultStatus.COMPLIANT


__all__ = ["SLDEngine"]
