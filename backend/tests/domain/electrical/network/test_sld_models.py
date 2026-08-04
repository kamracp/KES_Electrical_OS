"""
Unit tests for source-integration and SLD domain models.
KESE-S2-M14
"""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

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


def make_node(
    *,
    code: str = "UTILITY-01",
    node_type: SLDNodeType = SLDNodeType.UTILITY_GRID,
    nominal_voltage_v: Decimal = Decimal("11000"),
    source_priority: int | None = 1,
    **overrides: object,
) -> SLDNodeInput:
    values: dict[str, object] = {
        "code": code,
        "name": code.replace("-", " ").title(),
        "node_type": node_type,
        "nominal_voltage_v": nominal_voltage_v,
        "rated_power_kva": Decimal("2500"),
        "source_priority": source_priority,
        "equipment_reference": f"EQ-{code}",
        "location": "Main Substation",
    }
    values.update(overrides)
    return SLDNodeInput(**values)


def make_connection(
    *,
    code: str = "GRID-HT",
    from_node_code: str = "UTILITY-01",
    to_node_code: str = "HT-01",
    **overrides: object,
) -> SLDConnectionInput:
    values: dict[str, object] = {
        "code": code,
        "name": code.replace("-", " ").title(),
        "from_node_code": from_node_code,
        "to_node_code": to_node_code,
        "connection_type": SLDConnectionType.CABLE,
        "switching_device": SwitchingDeviceType.VCB,
        "normally_closed": True,
        "circuit_reference": f"CKT-{code}",
        "protection_reference": f"RLY-{code}",
        "cable_reference": f"CBL-{code}",
    }
    values.update(overrides)
    return SLDConnectionInput(**values)


def make_interlock(**overrides: object) -> SLDInterlockInput:
    values: dict[str, object] = {
        "code": "IL-PCC-INCOMERS",
        "name": "PCC Incomer Mutual Interlock",
        "connection_codes": ("TX-PCC", "DG-PCC"),
        "maximum_simultaneously_closed": 1,
        "failure_state": InterlockFailureState.TRIP_ALL,
        "hardwired": True,
    }
    values.update(overrides)
    return SLDInterlockInput(**values)


def make_state(
    *,
    code: str = "STATE-NORMAL",
    mode: OperatingMode = OperatingMode.NORMAL,
    active_source_codes: tuple[str, ...] = ("UTILITY-01",),
    closed_connection_codes: tuple[str, ...] = (
        "GRID-HT",
        "HT-TX",
        "TX-PCC",
        "PCC-LOAD",
    ),
    **overrides: object,
) -> SLDOperatingStateInput:
    values: dict[str, object] = {
        "code": code,
        "name": code.replace("-", " ").title(),
        "mode": mode,
        "active_source_codes": active_source_codes,
        "closed_connection_codes": closed_connection_codes,
    }
    values.update(overrides)
    return SLDOperatingStateInput(**values)


def make_network(**overrides: object) -> SLDNetworkInput:
    nodes = (
        make_node(),
        make_node(
            code="HT-01",
            node_type=SLDNodeType.HT_SWITCHGEAR,
            source_priority=None,
        ),
        make_node(
            code="TX-01",
            node_type=SLDNodeType.TRANSFORMER,
            source_priority=None,
        ),
        make_node(
            code="PCC-01",
            node_type=SLDNodeType.LT_PCC,
            nominal_voltage_v=Decimal("415"),
            source_priority=None,
        ),
        make_node(
            code="DG-01",
            node_type=SLDNodeType.GENERATOR,
            nominal_voltage_v=Decimal("415"),
            source_priority=2,
            rated_power_kva=Decimal("1000"),
        ),
        make_node(
            code="LOAD-01",
            node_type=SLDNodeType.FINAL_LOAD,
            nominal_voltage_v=Decimal("415"),
            source_priority=None,
            rated_power_kva=Decimal("800"),
        ),
    )
    connections = (
        make_connection(),
        make_connection(
            code="HT-TX",
            from_node_code="HT-01",
            to_node_code="TX-01",
        ),
        make_connection(
            code="TX-PCC",
            from_node_code="TX-01",
            to_node_code="PCC-01",
            switching_device=SwitchingDeviceType.ACB,
        ),
        make_connection(
            code="DG-PCC",
            from_node_code="DG-01",
            to_node_code="PCC-01",
            switching_device=SwitchingDeviceType.ACB,
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
            isolated_node_codes=("UTILITY-01", "HT-01", "TX-01"),
        ),
    )
    values: dict[str, object] = {
        "code": "SLD-PLANT-01",
        "name": "Plant Main Single Line Diagram",
        "nodes": nodes,
        "connections": connections,
        "operating_states": states,
        "interlocks": (make_interlock(),),
        "standard_reference": "IEC 60364",
    }
    values.update(overrides)
    return SLDNetworkInput(**values)


@pytest.mark.unit
def test_create_valid_sld_network() -> None:
    network = make_network()

    assert network.code == "SLD-PLANT-01"
    assert len(network.nodes) == 6
    assert len(network.connections) == 5
    assert len(network.operating_states) == 2
    assert network.interlocks[0].failure_state is InterlockFailureState.TRIP_ALL


@pytest.mark.unit
def test_sld_records_are_immutable() -> None:
    node = make_node()

    with pytest.raises(FrozenInstanceError):
        node.name = "Changed"


@pytest.mark.unit
def test_node_text_is_normalized() -> None:
    node = make_node(
        code="  UTILITY-01  ",
        name="  Utility Grid  ",
        notes="  Primary source  ",
    )

    assert node.code == "UTILITY-01"
    assert node.name == "Utility Grid"
    assert node.notes == "Primary source"


@pytest.mark.unit
def test_source_node_requires_priority() -> None:
    with pytest.raises(ValueError, match="source nodes require source_priority"):
        make_node(source_priority=None)


@pytest.mark.unit
def test_non_source_node_rejects_source_priority() -> None:
    with pytest.raises(ValueError, match="permitted only for source nodes"):
        make_node(node_type=SLDNodeType.LT_PCC)


@pytest.mark.unit
def test_node_rejects_float_voltage() -> None:
    with pytest.raises(TypeError, match="nominal_voltage_v must be a Decimal"):
        make_node(nominal_voltage_v=11000.0)


@pytest.mark.unit
def test_connection_rejects_self_loop() -> None:
    with pytest.raises(ValueError, match="cannot connect a node to itself"):
        make_connection(to_node_code="UTILITY-01")


@pytest.mark.unit
def test_transfer_mode_requires_switching_device() -> None:
    with pytest.raises(ValueError, match="transfer_mode requires"):
        make_connection(
            switching_device=SwitchingDeviceType.NONE,
            transfer_mode=TransferMode.MANUAL,
        )


@pytest.mark.unit
def test_closed_transition_requires_synchronization() -> None:
    with pytest.raises(ValueError, match="requires synchronization"):
        make_connection(
            transfer_mode=TransferMode.CLOSED_TRANSITION,
            synchronization_policy=SynchronizationPolicy.PERMITTED,
        )


@pytest.mark.unit
def test_static_transfer_requires_static_transfer_switch() -> None:
    with pytest.raises(ValueError, match="requires a STATIC_TRANSFER_SWITCH"):
        make_connection(
            transfer_mode=TransferMode.STATIC,
            switching_device=SwitchingDeviceType.ACB,
        )


@pytest.mark.unit
def test_valid_static_transfer_connection() -> None:
    connection = make_connection(
        transfer_mode=TransferMode.STATIC,
        switching_device=SwitchingDeviceType.STATIC_TRANSFER_SWITCH,
    )

    assert connection.transfer_mode is TransferMode.STATIC


@pytest.mark.unit
def test_interlock_requires_two_unique_connections() -> None:
    with pytest.raises(ValueError, match="requires at least two"):
        make_interlock(connection_codes=("TX-PCC",))

    with pytest.raises(ValueError, match="codes must be unique"):
        make_interlock(connection_codes=("TX-PCC", "TX-PCC"))


@pytest.mark.unit
def test_interlock_limit_must_create_real_exclusion() -> None:
    with pytest.raises(ValueError, match="must be below the number"):
        make_interlock(maximum_simultaneously_closed=2)


@pytest.mark.unit
def test_operating_state_requires_active_source() -> None:
    with pytest.raises(ValueError, match="requires at least one active source"):
        make_state(active_source_codes=())


@pytest.mark.unit
def test_operating_state_values_must_be_unique() -> None:
    with pytest.raises(ValueError, match="active_source_codes values must be unique"):
        make_state(active_source_codes=("UTILITY-01", "UTILITY-01"))


@pytest.mark.unit
def test_network_rejects_duplicate_node_codes() -> None:
    network = make_network()

    with pytest.raises(ValueError, match="node codes must be unique"):
        make_network(nodes=(*network.nodes, network.nodes[0]))


@pytest.mark.unit
def test_network_rejects_unknown_connection_node() -> None:
    network = make_network()
    invalid_connection = make_connection(
        code="UNKNOWN-PCC",
        from_node_code="UNKNOWN",
        to_node_code="PCC-01",
    )

    with pytest.raises(ValueError, match="unknown from_node_code"):
        make_network(connections=(*network.connections, invalid_connection))


@pytest.mark.unit
def test_voltage_change_requires_transformer_boundary() -> None:
    network = make_network()
    invalid_connection = make_connection(
        code="HT-PCC-DIRECT",
        from_node_code="HT-01",
        to_node_code="PCC-01",
    )

    with pytest.raises(ValueError, match="unequal voltages without a transformer"):
        make_network(connections=(*network.connections, invalid_connection))


@pytest.mark.unit
def test_operating_state_rejects_unknown_source() -> None:
    network = make_network()
    invalid_state = make_state(
        code="STATE-UNKNOWN-SOURCE",
        active_source_codes=("UNKNOWN-SOURCE",),
    )

    with pytest.raises(ValueError, match="unknown source nodes"):
        make_network(operating_states=(*network.operating_states, invalid_state))


@pytest.mark.unit
def test_operating_state_rejects_unknown_connection() -> None:
    network = make_network()
    invalid_state = make_state(
        code="STATE-UNKNOWN-CONNECTION",
        closed_connection_codes=("UNKNOWN-CONNECTION",),
    )

    with pytest.raises(ValueError, match="unknown connections"):
        make_network(operating_states=(*network.operating_states, invalid_state))


@pytest.mark.unit
def test_active_source_cannot_be_isolated() -> None:
    network = make_network()
    invalid_state = make_state(
        code="STATE-ISOLATED-SOURCE",
        isolated_node_codes=("UTILITY-01",),
    )

    with pytest.raises(ValueError, match="active source cannot be isolated"):
        make_network(operating_states=(*network.operating_states, invalid_state))


@pytest.mark.unit
def test_interlock_rejects_unknown_connection() -> None:
    with pytest.raises(ValueError, match="references unknown connections"):
        make_network(interlocks=(make_interlock(connection_codes=("TX-PCC", "UNKNOWN")),))


@pytest.mark.unit
def test_operating_state_cannot_violate_interlock() -> None:
    network = make_network()
    invalid_state = make_state(
        code="STATE-PARALLEL",
        active_source_codes=("UTILITY-01", "DG-01"),
        closed_connection_codes=(
            "GRID-HT",
            "HT-TX",
            "TX-PCC",
            "DG-PCC",
            "PCC-LOAD",
        ),
    )

    with pytest.raises(ValueError, match="violates interlock"):
        make_network(operating_states=(*network.operating_states, invalid_state))
