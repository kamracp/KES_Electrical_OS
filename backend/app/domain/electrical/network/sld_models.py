"""
Immutable source-integration and single-line-diagram domain models.
KESE-S2-M14
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.sources.common import (
    normalize_optional_text,
    normalize_required_text,
    require_positive_decimal,
)


class SLDNodeType(StrEnum):
    """Supported electrical network node types."""

    UTILITY_GRID = "UTILITY_GRID"
    HT_SWITCHGEAR = "HT_SWITCHGEAR"
    TRANSFORMER = "TRANSFORMER"
    GENERATOR = "GENERATOR"
    SOLAR_PV = "SOLAR_PV"
    UPS = "UPS"
    LT_PCC = "LT_PCC"
    DISTRIBUTION_PANEL = "DISTRIBUTION_PANEL"
    BUS_SECTION = "BUS_SECTION"
    BUS_COUPLER = "BUS_COUPLER"
    FINAL_LOAD = "FINAL_LOAD"


class SLDConnectionType(StrEnum):
    """Physical or logical connection represented on the SLD."""

    CABLE = "CABLE"
    BUSBAR = "BUSBAR"
    BUSDUCT = "BUSDUCT"
    SWITCHED_LINK = "SWITCHED_LINK"
    DIRECT = "DIRECT"


class SwitchingDeviceType(StrEnum):
    """Switching device controlling an SLD connection."""

    NONE = "NONE"
    ACB = "ACB"
    MCCB = "MCCB"
    MCB = "MCB"
    VCB = "VCB"
    LOAD_BREAK_SWITCH = "LOAD_BREAK_SWITCH"
    SWITCH_DISCONNECTOR = "SWITCH_DISCONNECTOR"
    STATIC_TRANSFER_SWITCH = "STATIC_TRANSFER_SWITCH"


class TransferMode(StrEnum):
    """Permitted source-transfer philosophy."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    MANUAL = "MANUAL"
    OPEN_TRANSITION = "OPEN_TRANSITION"
    CLOSED_TRANSITION = "CLOSED_TRANSITION"
    STATIC = "STATIC"


class SynchronizationPolicy(StrEnum):
    """Synchronization requirement for closing a connection."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    PROHIBITED = "PROHIBITED"
    REQUIRED = "REQUIRED"
    PERMITTED = "PERMITTED"


class OperatingMode(StrEnum):
    """Controlled network operating modes."""

    NORMAL = "NORMAL"
    EMERGENCY = "EMERGENCY"
    MAINTENANCE = "MAINTENANCE"
    ISLANDED = "ISLANDED"
    BLACK_START = "BLACK_START"


class InterlockFailureState(StrEnum):
    """Required connection state following interlock-control failure."""

    HOLD_LAST_STATE = "HOLD_LAST_STATE"
    TRIP_ALL = "TRIP_ALL"


_SOURCE_NODE_TYPES = {
    SLDNodeType.UTILITY_GRID,
    SLDNodeType.GENERATOR,
    SLDNodeType.SOLAR_PV,
    SLDNodeType.UPS,
}


def _require_positive_integer(field_name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer")
    if value < 1:
        raise ValueError(f"{field_name} must be at least 1")


@dataclass(frozen=True, slots=True)
class SLDNodeInput:
    """Immutable equipment or bus node in an electrical SLD graph."""

    code: str
    name: str
    node_type: SLDNodeType
    nominal_voltage_v: Decimal

    rated_power_kva: Decimal | None = None
    source_priority: int | None = None
    normally_energized: bool = True
    enabled: bool = True

    equipment_reference: str | None = None
    location: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize an SLD node."""

        object.__setattr__(self, "code", normalize_required_text("code", self.code))
        object.__setattr__(self, "name", normalize_required_text("name", self.name))

        for field_name in ("equipment_reference", "location", "notes"):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(field_name, getattr(self, field_name)),
            )

        if not isinstance(self.node_type, SLDNodeType):
            raise TypeError("node_type must be an SLDNodeType value")

        require_positive_decimal("nominal_voltage_v", self.nominal_voltage_v)
        if self.rated_power_kva is not None:
            require_positive_decimal("rated_power_kva", self.rated_power_kva)

        if self.source_priority is not None:
            _require_positive_integer("source_priority", self.source_priority)
            if self.node_type not in _SOURCE_NODE_TYPES:
                raise ValueError("source_priority is permitted only for source nodes")

        if self.node_type in _SOURCE_NODE_TYPES and self.source_priority is None:
            raise ValueError("source nodes require source_priority")


@dataclass(frozen=True, slots=True)
class SLDConnectionInput:
    """Immutable directed connection between two SLD nodes."""

    code: str
    name: str
    from_node_code: str
    to_node_code: str
    connection_type: SLDConnectionType
    switching_device: SwitchingDeviceType

    normally_closed: bool = True
    bidirectional_power_flow: bool = False
    transfer_mode: TransferMode = TransferMode.NOT_APPLICABLE
    synchronization_policy: SynchronizationPolicy = SynchronizationPolicy.NOT_APPLICABLE

    circuit_reference: str | None = None
    protection_reference: str | None = None
    cable_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize an SLD connection."""

        for field_name in ("code", "name", "from_node_code", "to_node_code"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(field_name, getattr(self, field_name)),
            )

        for field_name in (
            "circuit_reference",
            "protection_reference",
            "cable_reference",
            "notes",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(field_name, getattr(self, field_name)),
            )

        enum_fields: tuple[tuple[str, object, type[StrEnum]], ...] = (
            ("connection_type", self.connection_type, SLDConnectionType),
            ("switching_device", self.switching_device, SwitchingDeviceType),
            ("transfer_mode", self.transfer_mode, TransferMode),
            ("synchronization_policy", self.synchronization_policy, SynchronizationPolicy),
        )
        for field_name, value, enum_type in enum_fields:
            if not isinstance(value, enum_type):
                raise TypeError(f"{field_name} must be a {enum_type.__name__} value")

        if self.from_node_code == self.to_node_code:
            raise ValueError("an SLD connection cannot connect a node to itself")

        if self.switching_device is SwitchingDeviceType.NONE:
            if self.transfer_mode is not TransferMode.NOT_APPLICABLE:
                raise ValueError("transfer_mode requires a switching device")
            if self.synchronization_policy is not SynchronizationPolicy.NOT_APPLICABLE:
                raise ValueError("synchronization_policy requires a switching device")

        if (
            self.transfer_mode is TransferMode.CLOSED_TRANSITION
            and self.synchronization_policy is not SynchronizationPolicy.REQUIRED
        ):
            raise ValueError("CLOSED_TRANSITION transfer requires synchronization")

        if (
            self.transfer_mode is TransferMode.STATIC
            and self.switching_device is not SwitchingDeviceType.STATIC_TRANSFER_SWITCH
        ):
            raise ValueError("STATIC transfer requires a STATIC_TRANSFER_SWITCH")


@dataclass(frozen=True, slots=True)
class SLDInterlockInput:
    """Mutual-exclusion rule for a group of switched connections."""

    code: str
    name: str
    connection_codes: tuple[str, ...]

    maximum_simultaneously_closed: int = 1
    failure_state: InterlockFailureState = InterlockFailureState.TRIP_ALL
    hardwired: bool = True
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize an interlock rule."""

        object.__setattr__(self, "code", normalize_required_text("code", self.code))
        object.__setattr__(self, "name", normalize_required_text("name", self.name))
        object.__setattr__(self, "notes", normalize_optional_text("notes", self.notes))

        if not isinstance(self.connection_codes, tuple):
            raise TypeError("connection_codes must be a tuple")
        if len(self.connection_codes) < 2:
            raise ValueError("an interlock requires at least two connections")

        normalized_codes = tuple(
            normalize_required_text("connection_code", code) for code in self.connection_codes
        )
        if len(normalized_codes) != len(set(normalized_codes)):
            raise ValueError("interlock connection codes must be unique")
        object.__setattr__(self, "connection_codes", normalized_codes)

        _require_positive_integer(
            "maximum_simultaneously_closed",
            self.maximum_simultaneously_closed,
        )
        if self.maximum_simultaneously_closed >= len(self.connection_codes):
            raise ValueError(
                "maximum_simultaneously_closed must be below the number of interlocked connections"
            )

        if not isinstance(self.failure_state, InterlockFailureState):
            raise TypeError("failure_state must be an InterlockFailureState value")


@dataclass(frozen=True, slots=True)
class SLDOperatingStateInput:
    """Connection and source state for one operating mode."""

    code: str
    name: str
    mode: OperatingMode
    active_source_codes: tuple[str, ...]
    closed_connection_codes: tuple[str, ...]

    isolated_node_codes: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize an operating state."""

        object.__setattr__(self, "code", normalize_required_text("code", self.code))
        object.__setattr__(self, "name", normalize_required_text("name", self.name))
        object.__setattr__(self, "notes", normalize_optional_text("notes", self.notes))

        if not isinstance(self.mode, OperatingMode):
            raise TypeError("mode must be an OperatingMode value")

        for field_name in (
            "active_source_codes",
            "closed_connection_codes",
            "isolated_node_codes",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise TypeError(f"{field_name} must be a tuple")
            normalized_values = tuple(
                normalize_required_text(field_name, value) for value in values
            )
            if len(normalized_values) != len(set(normalized_values)):
                raise ValueError(f"{field_name} values must be unique")
            object.__setattr__(self, field_name, normalized_values)

        if not self.active_source_codes:
            raise ValueError("an operating state requires at least one active source")


@dataclass(frozen=True, slots=True)
class SLDNetworkInput:
    """Complete immutable source-integration and SLD network input."""

    code: str
    name: str
    nodes: tuple[SLDNodeInput, ...]
    connections: tuple[SLDConnectionInput, ...]
    operating_states: tuple[SLDOperatingStateInput, ...]

    interlocks: tuple[SLDInterlockInput, ...] = ()
    standard_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate the complete graph and its operating states."""

        object.__setattr__(self, "code", normalize_required_text("code", self.code))
        object.__setattr__(self, "name", normalize_required_text("name", self.name))
        object.__setattr__(
            self,
            "standard_reference",
            normalize_optional_text("standard_reference", self.standard_reference),
        )
        object.__setattr__(self, "notes", normalize_optional_text("notes", self.notes))

        record_collections: tuple[tuple[str, tuple[object, ...], type[object]], ...] = (
            ("nodes", self.nodes, SLDNodeInput),
            ("connections", self.connections, SLDConnectionInput),
            ("operating_states", self.operating_states, SLDOperatingStateInput),
            ("interlocks", self.interlocks, SLDInterlockInput),
        )
        for field_name, records, record_type in record_collections:
            if not isinstance(records, tuple):
                raise TypeError(f"{field_name} must be a tuple")
            if not all(isinstance(record, record_type) for record in records):
                raise TypeError(f"{field_name} must contain only {record_type.__name__} records")

        if not self.nodes:
            raise ValueError("an SLD network requires at least one node")
        if not self.connections:
            raise ValueError("an SLD network requires at least one connection")
        if not self.operating_states:
            raise ValueError("an SLD network requires at least one operating state")

        node_by_code = {node.code: node for node in self.nodes}
        if len(node_by_code) != len(self.nodes):
            raise ValueError("node codes must be unique")

        connection_by_code = {connection.code: connection for connection in self.connections}
        if len(connection_by_code) != len(self.connections):
            raise ValueError("connection codes must be unique")

        operating_state_codes = {state.code for state in self.operating_states}
        if len(operating_state_codes) != len(self.operating_states):
            raise ValueError("operating state codes must be unique")

        interlock_codes = {interlock.code for interlock in self.interlocks}
        if len(interlock_codes) != len(self.interlocks):
            raise ValueError("interlock codes must be unique")

        for connection in self.connections:
            if connection.from_node_code not in node_by_code:
                raise ValueError(f"connection {connection.code} references unknown from_node_code")
            if connection.to_node_code not in node_by_code:
                raise ValueError(f"connection {connection.code} references unknown to_node_code")

            from_node = node_by_code[connection.from_node_code]
            to_node = node_by_code[connection.to_node_code]
            if (
                from_node.nominal_voltage_v != to_node.nominal_voltage_v
                and SLDNodeType.TRANSFORMER not in {from_node.node_type, to_node.node_type}
            ):
                raise ValueError(
                    f"connection {connection.code} joins unequal voltages without a transformer"
                )

        source_codes = {node.code for node in self.nodes if node.node_type in _SOURCE_NODE_TYPES}
        for operating_state in self.operating_states:
            unknown_sources = set(operating_state.active_source_codes) - source_codes
            if unknown_sources:
                raise ValueError(
                    f"operating state {operating_state.code} references unknown source nodes"
                )

            unknown_connections = (
                set(operating_state.closed_connection_codes) - connection_by_code.keys()
            )
            if unknown_connections:
                raise ValueError(
                    f"operating state {operating_state.code} references unknown connections"
                )

            unknown_isolated_nodes = set(operating_state.isolated_node_codes) - node_by_code.keys()
            if unknown_isolated_nodes:
                raise ValueError(
                    f"operating state {operating_state.code} references unknown isolated nodes"
                )
            if set(operating_state.active_source_codes) & set(operating_state.isolated_node_codes):
                raise ValueError("an active source cannot be isolated in the same operating state")

        for interlock in self.interlocks:
            unknown_interlocked_connections = (
                set(interlock.connection_codes) - connection_by_code.keys()
            )
            if unknown_interlocked_connections:
                raise ValueError(f"interlock {interlock.code} references unknown connections")
            for operating_state in self.operating_states:
                closed_count = len(
                    set(interlock.connection_codes) & set(operating_state.closed_connection_codes)
                )
                if closed_count > interlock.maximum_simultaneously_closed:
                    message = (
                        f"operating state {operating_state.code} violates "
                        f"interlock {interlock.code}"
                    )
                    raise ValueError(message)


__all__ = [
    "InterlockFailureState",
    "OperatingMode",
    "SLDConnectionInput",
    "SLDConnectionType",
    "SLDInterlockInput",
    "SLDNetworkInput",
    "SLDNodeInput",
    "SLDNodeType",
    "SLDOperatingStateInput",
    "SwitchingDeviceType",
    "SynchronizationPolicy",
    "TransferMode",
]
