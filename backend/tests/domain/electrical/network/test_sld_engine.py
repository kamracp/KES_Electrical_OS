"""
Unit tests for the source-integration and SLD evaluation engine.
KESE-S2-M14
"""

from decimal import Decimal

import pytest

from app.domain.electrical.network.sld_engine import SLDEngine
from app.domain.electrical.network.sld_models import (
    InterlockFailureState,
    OperatingMode,
    SLDConnectionInput,
    SLDConnectionType,
    SLDInterlockInput,
    SLDNetworkInput,
    SLDNodeInput,
    SLDNodeType,
    SLDOperatingStateInput,
    SwitchingDeviceType,
    SynchronizationPolicy,
    TransferMode,
)
from app.domain.electrical.network.sld_results import (
    SLDCheckStatus,
    SLDResultStatus,
    SLDWarningCode,
)


def make_node(
    *,
    code: str,
    node_type: SLDNodeType,
    source_priority: int | None = None,
    **overrides: object,
) -> SLDNodeInput:
    values: dict[str, object] = {
        "code": code,
        "name": code.replace("-", " ").title(),
        "node_type": node_type,
        "nominal_voltage_v": Decimal("415"),
        "rated_power_kva": Decimal("1000"),
        "source_priority": source_priority,
        "equipment_reference": f"EQ-{code}",
    }
    values.update(overrides)
    return SLDNodeInput(**values)


def make_connection(
    *,
    code: str,
    from_node_code: str,
    to_node_code: str,
    **overrides: object,
) -> SLDConnectionInput:
    values: dict[str, object] = {
        "code": code,
        "name": code.replace("-", " ").title(),
        "from_node_code": from_node_code,
        "to_node_code": to_node_code,
        "connection_type": SLDConnectionType.CABLE,
        "switching_device": SwitchingDeviceType.ACB,
        "normally_closed": True,
        "circuit_reference": f"CKT-{code}",
    }
    values.update(overrides)
    return SLDConnectionInput(**values)


def make_state(
    *,
    code: str = "STATE-NORMAL",
    mode: OperatingMode = OperatingMode.NORMAL,
    active_source_codes: tuple[str, ...] = ("UTILITY-01",),
    closed_connection_codes: tuple[str, ...] = ("GRID-PCC", "PCC-LOAD"),
    isolated_node_codes: tuple[str, ...] = (),
) -> SLDOperatingStateInput:
    return SLDOperatingStateInput(
        code=code,
        name=code.replace("-", " ").title(),
        mode=mode,
        active_source_codes=active_source_codes,
        closed_connection_codes=closed_connection_codes,
        isolated_node_codes=isolated_node_codes,
    )


def make_network(**overrides: object) -> SLDNetworkInput:
    nodes = (
        make_node(
            code="UTILITY-01",
            node_type=SLDNodeType.UTILITY_GRID,
            source_priority=1,
        ),
        make_node(code="PCC-01", node_type=SLDNodeType.LT_PCC),
        make_node(
            code="DG-01",
            node_type=SLDNodeType.GENERATOR,
            source_priority=2,
        ),
        make_node(code="LOAD-01", node_type=SLDNodeType.FINAL_LOAD),
    )
    connections = (
        make_connection(
            code="GRID-PCC",
            from_node_code="UTILITY-01",
            to_node_code="PCC-01",
        ),
        make_connection(
            code="DG-PCC",
            from_node_code="DG-01",
            to_node_code="PCC-01",
            normally_closed=False,
            transfer_mode=TransferMode.OPEN_TRANSITION,
            synchronization_policy=SynchronizationPolicy.PROHIBITED,
        ),
        make_connection(
            code="PCC-LOAD",
            from_node_code="PCC-01",
            to_node_code="LOAD-01",
            switching_device=SwitchingDeviceType.MCCB,
        ),
    )
    states = (
        make_state(),
        make_state(
            code="STATE-EMERGENCY",
            mode=OperatingMode.EMERGENCY,
            active_source_codes=("DG-01",),
            closed_connection_codes=("DG-PCC", "PCC-LOAD"),
            isolated_node_codes=("UTILITY-01",),
        ),
    )
    interlock = SLDInterlockInput(
        code="IL-INCOMERS",
        name="PCC Incomer Mutual Interlock",
        connection_codes=("GRID-PCC", "DG-PCC"),
        maximum_simultaneously_closed=1,
        failure_state=InterlockFailureState.TRIP_ALL,
    )
    values: dict[str, object] = {
        "code": "SLD-01",
        "name": "Plant Main SLD",
        "nodes": nodes,
        "connections": connections,
        "operating_states": states,
        "interlocks": (interlock,),
        "standard_reference": "IEC 60364",
    }
    values.update(overrides)
    return SLDNetworkInput(**values)


def warning_codes(result: object) -> set[SLDWarningCode]:
    return {warning.code for warning in result.warnings}


@pytest.mark.unit
def test_evaluate_normal_state_from_utility() -> None:
    result = SLDEngine.evaluate_operating_state(make_network(), "STATE-NORMAL")
    nodes = {node.node_code: node for node in result.node_results}
    sources = {source.source_code: source for source in result.source_results}

    assert result.status is SLDResultStatus.DESIGN_CHECK_PASSED
    assert result.primary_source_code == "UTILITY-01"
    assert result.final_load_supply_percent == Decimal("100")
    assert nodes["LOAD-01"].energized is True
    assert nodes["LOAD-01"].supplying_source_codes == ("UTILITY-01",)
    assert sources["DG-01"].active is False
    assert sources["DG-01"].supplied_node_codes == ()
    assert result.warnings == ()


@pytest.mark.unit
def test_evaluate_emergency_state_from_generator() -> None:
    result = SLDEngine.evaluate_operating_state(make_network(), "STATE-EMERGENCY")
    nodes = {node.node_code: node for node in result.node_results}

    assert result.status is SLDResultStatus.DESIGN_CHECK_PASSED
    assert result.primary_source_code == "DG-01"
    assert result.final_load_supply_percent == Decimal("100")
    assert nodes["UTILITY-01"].isolated is True
    assert nodes["UTILITY-01"].energized is False
    assert nodes["LOAD-01"].supplying_source_codes == ("DG-01",)


@pytest.mark.unit
def test_evaluate_complete_network() -> None:
    result = SLDEngine.evaluate(make_network())

    assert result.status is SLDResultStatus.DESIGN_CHECK_PASSED
    assert tuple(state.state_code for state in result.operating_state_results) == (
        "STATE-NORMAL",
        "STATE-EMERGENCY",
    )
    assert result.compliant_state_count == 2
    assert result.standard_reference == "IEC 60364"


@pytest.mark.unit
def test_engine_requires_network_input() -> None:
    with pytest.raises(TypeError, match="SLDNetworkInput"):
        SLDEngine.evaluate("SLD-01")

    with pytest.raises(TypeError, match="SLDNetworkInput"):
        SLDEngine.evaluate_operating_state("SLD-01", "STATE-NORMAL")


@pytest.mark.unit
def test_unknown_operating_state_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown operating state code"):
        SLDEngine.evaluate_operating_state(make_network(), "UNKNOWN")


@pytest.mark.unit
def test_state_code_is_normalized() -> None:
    result = SLDEngine.evaluate_operating_state(
        make_network(),
        "  STATE-NORMAL  ",
    )

    assert result.state_code == "STATE-NORMAL"


@pytest.mark.unit
def test_open_load_connection_reports_unsupplied_final_load() -> None:
    state = make_state(closed_connection_codes=("GRID-PCC",))
    network = make_network(operating_states=(state,))

    result = SLDEngine.evaluate(network)

    assert result.status is SLDResultStatus.DESIGN_CHECK_FAILED
    assert result.operating_state_results[0].final_load_supply_percent == Decimal("0")
    assert SLDWarningCode.FINAL_LOAD_UNSUPPLIED in warning_codes(result.operating_state_results[0])


@pytest.mark.unit
def test_disabled_active_source_reports_no_primary_source() -> None:
    network = make_network()
    disabled_utility = make_node(
        code="UTILITY-01",
        node_type=SLDNodeType.UTILITY_GRID,
        source_priority=1,
        enabled=False,
    )
    nodes = (disabled_utility, *network.nodes[1:])
    normal_state = make_state(closed_connection_codes=("GRID-PCC", "PCC-LOAD"))
    network = make_network(nodes=nodes, operating_states=(normal_state,))

    result = SLDEngine.evaluate(network).operating_state_results[0]

    assert result.status is SLDResultStatus.DESIGN_CHECK_FAILED
    assert result.primary_source_code is None
    assert SLDWarningCode.ACTIVE_SOURCE_DISABLED in warning_codes(result)
    assert SLDWarningCode.NO_PRIMARY_SOURCE in warning_codes(result)


@pytest.mark.unit
def test_disabled_priority_source_falls_back_to_generator() -> None:
    network = make_network()
    disabled_utility = make_node(
        code="UTILITY-01",
        node_type=SLDNodeType.UTILITY_GRID,
        source_priority=1,
        enabled=False,
    )
    nodes = (disabled_utility, *network.nodes[1:])
    fallback_state = make_state(
        code="STATE-FALLBACK",
        mode=OperatingMode.EMERGENCY,
        active_source_codes=("UTILITY-01", "DG-01"),
        closed_connection_codes=("DG-PCC", "PCC-LOAD"),
    )
    network = make_network(nodes=nodes, operating_states=(fallback_state,))

    result = SLDEngine.evaluate(network).operating_state_results[0]

    assert result.primary_source_code == "DG-01"
    assert result.final_load_supply_percent == Decimal("100")
    assert SLDWarningCode.SOURCE_PRIORITY_BYPASSED in warning_codes(result)
    assert SLDWarningCode.ACTIVE_SOURCE_DISABLED in warning_codes(result)


@pytest.mark.unit
def test_disabled_intermediate_node_stops_power_propagation() -> None:
    network = make_network()
    disabled_pcc = make_node(
        code="PCC-01",
        node_type=SLDNodeType.LT_PCC,
        enabled=False,
    )
    nodes = (network.nodes[0], disabled_pcc, *network.nodes[2:])
    network = make_network(nodes=nodes, operating_states=(make_state(),))

    result = SLDEngine.evaluate(network).operating_state_results[0]
    node_results = {node.node_code: node for node in result.node_results}

    assert node_results["UTILITY-01"].energized is True
    assert node_results["PCC-01"].energized is False
    assert node_results["LOAD-01"].energized is False
    assert SLDWarningCode.FINAL_LOAD_UNSUPPLIED in warning_codes(result)
    assert SLDWarningCode.CLOSED_CONNECTION_UNENERGIZED in warning_codes(result)


@pytest.mark.unit
def test_isolated_load_stops_propagation_without_unsupplied_warning() -> None:
    state = make_state(isolated_node_codes=("LOAD-01",))
    network = make_network(operating_states=(state,))

    result = SLDEngine.evaluate(network).operating_state_results[0]
    load = next(node for node in result.node_results if node.node_code == "LOAD-01")

    assert result.status is SLDResultStatus.DESIGN_CHECK_PASSED
    assert load.isolated is True
    assert load.energized is False
    assert SLDWarningCode.FINAL_LOAD_UNSUPPLIED not in warning_codes(result)


@pytest.mark.unit
def test_bidirectional_connection_allows_reverse_reachability() -> None:
    nodes = (
        make_node(
            code="UTILITY-01",
            node_type=SLDNodeType.UTILITY_GRID,
            source_priority=1,
        ),
        make_node(code="LOAD-01", node_type=SLDNodeType.FINAL_LOAD),
    )
    connection = make_connection(
        code="LOAD-GRID",
        from_node_code="LOAD-01",
        to_node_code="UTILITY-01",
        bidirectional_power_flow=True,
    )
    state = make_state(closed_connection_codes=("LOAD-GRID",))
    network = make_network(
        nodes=nodes,
        connections=(connection,),
        operating_states=(state,),
        interlocks=(),
    )

    result = SLDEngine.evaluate(network).operating_state_results[0]

    assert result.status is SLDResultStatus.DESIGN_CHECK_PASSED
    assert result.final_load_supply_percent == Decimal("100")
    assert SLDWarningCode.REVERSE_POWER_FLOW_BLOCKED not in warning_codes(result)


@pytest.mark.unit
def test_unidirectional_connection_blocks_reverse_reachability() -> None:
    nodes = (
        make_node(
            code="UTILITY-01",
            node_type=SLDNodeType.UTILITY_GRID,
            source_priority=1,
        ),
        make_node(code="LOAD-01", node_type=SLDNodeType.FINAL_LOAD),
    )
    connection = make_connection(
        code="LOAD-GRID",
        from_node_code="LOAD-01",
        to_node_code="UTILITY-01",
    )
    state = make_state(closed_connection_codes=("LOAD-GRID",))
    network = make_network(
        nodes=nodes,
        connections=(connection,),
        operating_states=(state,),
        interlocks=(),
    )

    result = SLDEngine.evaluate(network).operating_state_results[0]

    assert result.status is SLDResultStatus.DESIGN_CHECK_FAILED
    assert result.final_load_supply_percent == Decimal("0")
    assert SLDWarningCode.REVERSE_POWER_FLOW_BLOCKED in warning_codes(result)


@pytest.mark.unit
def test_parallel_sources_are_reported() -> None:
    parallel_state = make_state(
        code="STATE-PARALLEL",
        active_source_codes=("UTILITY-01", "DG-01"),
        closed_connection_codes=("GRID-PCC", "DG-PCC", "PCC-LOAD"),
    )
    network = make_network(
        operating_states=(parallel_state,),
        interlocks=(),
    )

    result = SLDEngine.evaluate(network).operating_state_results[0]
    load = next(node for node in result.node_results if node.node_code == "LOAD-01")

    assert result.status is SLDResultStatus.REVIEW_REQUIRED
    assert result.primary_source_code == "UTILITY-01"
    assert load.supplying_source_codes == ("UTILITY-01", "DG-01")
    assert SLDWarningCode.MULTIPLE_ACTIVE_SOURCES in warning_codes(result)


@pytest.mark.unit
def test_closed_transition_requires_synchronization_verification() -> None:
    network = make_network()
    closed_transition = make_connection(
        code="DG-PCC",
        from_node_code="DG-01",
        to_node_code="PCC-01",
        normally_closed=False,
        transfer_mode=TransferMode.CLOSED_TRANSITION,
        synchronization_policy=SynchronizationPolicy.REQUIRED,
    )
    connections = (
        network.connections[0],
        closed_transition,
        network.connections[2],
    )
    emergency_state = make_state(
        code="STATE-CLOSED-TRANSFER",
        mode=OperatingMode.EMERGENCY,
        active_source_codes=("DG-01",),
        closed_connection_codes=("DG-PCC", "PCC-LOAD"),
        isolated_node_codes=("UTILITY-01",),
    )
    network = make_network(
        connections=connections,
        operating_states=(emergency_state,),
    )

    result = SLDEngine.evaluate(network).operating_state_results[0]

    assert result.status is SLDResultStatus.REVIEW_REQUIRED
    assert SLDWarningCode.SYNCHRONIZATION_REQUIRED in warning_codes(result)


@pytest.mark.unit
def test_closed_deenergized_connection_is_reported() -> None:
    network = make_network()
    ups = make_node(
        code="UPS-01",
        node_type=SLDNodeType.UPS,
        source_priority=3,
    )
    inactive_link = make_connection(
        code="DG-UPS",
        from_node_code="DG-01",
        to_node_code="UPS-01",
    )
    state = make_state(
        closed_connection_codes=("GRID-PCC", "PCC-LOAD", "DG-UPS"),
    )
    network = make_network(
        nodes=(*network.nodes, ups),
        connections=(*network.connections, inactive_link),
        operating_states=(state,),
    )

    result = SLDEngine.evaluate(network).operating_state_results[0]
    connection = next(
        item for item in result.connection_results if item.connection_code == "DG-UPS"
    )

    assert result.status is SLDResultStatus.REVIEW_REQUIRED
    assert connection.closed is True
    assert connection.energized is False
    assert SLDWarningCode.CLOSED_CONNECTION_UNENERGIZED in warning_codes(result)


@pytest.mark.unit
def test_intentionally_deenergized_load_does_not_warn() -> None:
    network = make_network()
    optional_load = make_node(
        code="LOAD-01",
        node_type=SLDNodeType.FINAL_LOAD,
        normally_energized=False,
    )
    nodes = (*network.nodes[:3], optional_load)
    state = make_state(closed_connection_codes=("GRID-PCC",))
    network = make_network(nodes=nodes, operating_states=(state,))

    result = SLDEngine.evaluate(network).operating_state_results[0]

    assert result.status is SLDResultStatus.DESIGN_CHECK_PASSED
    assert result.final_load_supply_percent == Decimal("0")
    assert SLDWarningCode.FINAL_LOAD_UNSUPPLIED not in warning_codes(result)


@pytest.mark.unit
def test_disabled_load_does_not_warn() -> None:
    network = make_network()
    disabled_load = make_node(
        code="LOAD-01",
        node_type=SLDNodeType.FINAL_LOAD,
        enabled=False,
    )
    nodes = (*network.nodes[:3], disabled_load)
    state = make_state(closed_connection_codes=("GRID-PCC",))
    network = make_network(nodes=nodes, operating_states=(state,))

    result = SLDEngine.evaluate(network).operating_state_results[0]

    assert result.status is SLDResultStatus.DESIGN_CHECK_PASSED
    assert result.enabled_final_load_count == 0
    assert result.final_load_supply_percent == Decimal("100")


@pytest.mark.unit
def test_connection_and_interlock_results_cover_complete_network() -> None:
    result = SLDEngine.evaluate_operating_state(make_network(), "STATE-NORMAL")
    connections = {
        connection.connection_code: connection for connection in result.connection_results
    }

    assert set(connections) == {"GRID-PCC", "DG-PCC", "PCC-LOAD"}
    assert connections["GRID-PCC"].closed is True
    assert connections["DG-PCC"].closed is False
    assert result.interlock_results[0].status is SLDCheckStatus.PASS
    assert result.interlock_results[0].closed_connection_codes == ("GRID-PCC",)


@pytest.mark.unit
def test_source_results_follow_engineering_priority() -> None:
    result = SLDEngine.evaluate_operating_state(make_network(), "STATE-NORMAL")

    assert tuple(source.source_code for source in result.source_results) == (
        "UTILITY-01",
        "DG-01",
    )
    assert tuple(source.priority for source in result.source_results) == (1, 2)
