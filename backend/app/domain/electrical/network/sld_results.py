"""
Immutable source-integration and single-line-diagram evaluation results.
KESE-S2-M14
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.network.sld_models import OperatingMode, SLDNodeType
from app.domain.electrical.sources.common import (
    normalize_optional_text,
    normalize_required_text,
)


class SLDResultStatus(StrEnum):
    """Outcome of an SLD engineering design check, not statutory compliance."""

    DESIGN_CHECK_PASSED = "DESIGN_CHECK_PASSED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    DESIGN_CHECK_FAILED = "DESIGN_CHECK_FAILED"

    # Temporary compatibility aliases for pre-KEOS-S2-M1 callers.
    COMPLIANT = DESIGN_CHECK_PASSED
    WARNING = REVIEW_REQUIRED
    NON_COMPLIANT = DESIGN_CHECK_FAILED


class SLDCheckStatus(StrEnum):
    """Outcome of a discrete SLD engineering check."""

    PASS = "PASS"
    FAIL = "FAIL"


class SLDWarningSeverity(StrEnum):
    """Engineering consequence assigned to an SLD warning."""

    WARNING = "WARNING"
    ERROR = "ERROR"


class SLDWarningCode(StrEnum):
    """Machine-readable source-integration and SLD warning codes."""

    ACTIVE_SOURCE_DISABLED = "ACTIVE_SOURCE_DISABLED"
    ENABLED_NODE_UNENERGIZED = "ENABLED_NODE_UNENERGIZED"
    FINAL_LOAD_UNSUPPLIED = "FINAL_LOAD_UNSUPPLIED"
    MULTIPLE_ACTIVE_SOURCES = "MULTIPLE_ACTIVE_SOURCES"
    SOURCE_PRIORITY_BYPASSED = "SOURCE_PRIORITY_BYPASSED"
    CLOSED_CONNECTION_UNENERGIZED = "CLOSED_CONNECTION_UNENERGIZED"
    INTERLOCK_VIOLATION = "INTERLOCK_VIOLATION"
    REVERSE_POWER_FLOW_BLOCKED = "REVERSE_POWER_FLOW_BLOCKED"
    SYNCHRONIZATION_REQUIRED = "SYNCHRONIZATION_REQUIRED"
    NO_PRIMARY_SOURCE = "NO_PRIMARY_SOURCE"


_SOURCE_NODE_TYPES = {
    SLDNodeType.UTILITY_GRID,
    SLDNodeType.GENERATOR,
    SLDNodeType.SOLAR_PV,
    SLDNodeType.UPS,
}


def _require_boolean(field_name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean")


def _require_positive_integer(field_name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer")
    if value < 1:
        raise ValueError(f"{field_name} must be at least 1")


def _normalize_unique_codes(field_name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple")

    normalized_values = tuple(normalize_required_text(field_name, value) for value in values)
    if len(normalized_values) != len(set(normalized_values)):
        raise ValueError(f"{field_name} values must be unique")
    return normalized_values


@dataclass(frozen=True, slots=True)
class SLDEngineeringWarning:
    """Structured warning emitted during SLD evaluation."""

    code: SLDWarningCode
    severity: SLDWarningSeverity
    message: str
    reference_code: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the warning."""

        if not isinstance(self.code, SLDWarningCode):
            raise TypeError("code must be an SLDWarningCode value")
        if not isinstance(self.severity, SLDWarningSeverity):
            raise TypeError("severity must be an SLDWarningSeverity value")

        object.__setattr__(
            self,
            "message",
            normalize_required_text("message", self.message),
        )
        object.__setattr__(
            self,
            "reference_code",
            normalize_optional_text("reference_code", self.reference_code),
        )


@dataclass(frozen=True, slots=True)
class SLDSourceStateResult:
    """Evaluated participation of one source in an operating state."""

    source_code: str
    priority: int
    active: bool
    primary: bool
    supplied_node_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate source selection and supplied-node references."""

        object.__setattr__(
            self,
            "source_code",
            normalize_required_text("source_code", self.source_code),
        )
        _require_positive_integer("priority", self.priority)
        _require_boolean("active", self.active)
        _require_boolean("primary", self.primary)
        object.__setattr__(
            self,
            "supplied_node_codes",
            _normalize_unique_codes("supplied_node_codes", self.supplied_node_codes),
        )

        if self.primary and not self.active:
            raise ValueError("a primary source must be active")
        if not self.active and self.supplied_node_codes:
            raise ValueError("an inactive source cannot supply nodes")


@dataclass(frozen=True, slots=True)
class SLDNodeStateResult:
    """Energization state and source reachability for one SLD node."""

    node_code: str
    node_type: SLDNodeType
    enabled: bool
    energized: bool
    isolated: bool
    supplying_source_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate node state consistency."""

        object.__setattr__(
            self,
            "node_code",
            normalize_required_text("node_code", self.node_code),
        )
        if not isinstance(self.node_type, SLDNodeType):
            raise TypeError("node_type must be an SLDNodeType value")

        for field_name in ("enabled", "energized", "isolated"):
            _require_boolean(field_name, getattr(self, field_name))

        object.__setattr__(
            self,
            "supplying_source_codes",
            _normalize_unique_codes(
                "supplying_source_codes",
                self.supplying_source_codes,
            ),
        )

        if self.isolated and self.energized:
            raise ValueError("an isolated node cannot be energized")
        if not self.enabled and self.energized:
            raise ValueError("a disabled node cannot be energized")
        if self.energized and not self.supplying_source_codes:
            raise ValueError("an energized node requires at least one supplying source")
        if not self.energized and self.supplying_source_codes:
            raise ValueError("a de-energized node cannot have supplying sources")


@dataclass(frozen=True, slots=True)
class SLDConnectionStateResult:
    """Evaluated open, closed, and energized state of one connection."""

    connection_code: str
    closed: bool
    energized: bool
    from_node_energized: bool
    to_node_energized: bool

    def __post_init__(self) -> None:
        """Validate connection-state consistency."""

        object.__setattr__(
            self,
            "connection_code",
            normalize_required_text("connection_code", self.connection_code),
        )
        for field_name in (
            "closed",
            "energized",
            "from_node_energized",
            "to_node_energized",
        ):
            _require_boolean(field_name, getattr(self, field_name))

        expected_energized = self.closed and (self.from_node_energized or self.to_node_energized)
        if self.energized is not expected_energized:
            raise ValueError("connection energized state must match its closed and endpoint states")


@dataclass(frozen=True, slots=True)
class SLDInterlockResult:
    """Evaluated mutual-exclusion status for one interlock."""

    interlock_code: str
    closed_connection_codes: tuple[str, ...]
    maximum_simultaneously_closed: int
    status: SLDCheckStatus

    def __post_init__(self) -> None:
        """Validate the interlock result and its check status."""

        object.__setattr__(
            self,
            "interlock_code",
            normalize_required_text("interlock_code", self.interlock_code),
        )
        object.__setattr__(
            self,
            "closed_connection_codes",
            _normalize_unique_codes(
                "closed_connection_codes",
                self.closed_connection_codes,
            ),
        )
        _require_positive_integer(
            "maximum_simultaneously_closed",
            self.maximum_simultaneously_closed,
        )

        if not isinstance(self.status, SLDCheckStatus):
            raise TypeError("status must be an SLDCheckStatus value")

        expected_status = (
            SLDCheckStatus.PASS
            if len(self.closed_connection_codes) <= self.maximum_simultaneously_closed
            else SLDCheckStatus.FAIL
        )
        if self.status is not expected_status:
            raise ValueError("interlock status does not match the closed connection count")


@dataclass(frozen=True, slots=True)
class SLDOperatingStateResult:
    """Complete auditable evaluation for one SLD operating state."""

    network_code: str
    state_code: str
    mode: OperatingMode
    status: SLDResultStatus
    primary_source_code: str | None
    source_results: tuple[SLDSourceStateResult, ...]
    node_results: tuple[SLDNodeStateResult, ...]
    connection_results: tuple[SLDConnectionStateResult, ...]
    interlock_results: tuple[SLDInterlockResult, ...] = ()
    warnings: tuple[SLDEngineeringWarning, ...] = ()

    def __post_init__(self) -> None:
        """Validate state-level result consistency and references."""

        object.__setattr__(
            self,
            "network_code",
            normalize_required_text("network_code", self.network_code),
        )
        object.__setattr__(
            self,
            "state_code",
            normalize_required_text("state_code", self.state_code),
        )
        object.__setattr__(
            self,
            "primary_source_code",
            normalize_optional_text("primary_source_code", self.primary_source_code),
        )

        if not isinstance(self.mode, OperatingMode):
            raise TypeError("mode must be an OperatingMode value")
        if not isinstance(self.status, SLDResultStatus):
            raise TypeError("status must be an SLDResultStatus value")

        collections: tuple[tuple[str, tuple[object, ...], type[object]], ...] = (
            ("source_results", self.source_results, SLDSourceStateResult),
            ("node_results", self.node_results, SLDNodeStateResult),
            ("connection_results", self.connection_results, SLDConnectionStateResult),
            ("interlock_results", self.interlock_results, SLDInterlockResult),
            ("warnings", self.warnings, SLDEngineeringWarning),
        )
        for field_name, records, record_type in collections:
            if not isinstance(records, tuple):
                raise TypeError(f"{field_name} must be a tuple")
            if not all(isinstance(record, record_type) for record in records):
                raise TypeError(f"{field_name} must contain only {record_type.__name__} records")

        if not self.source_results:
            raise ValueError("an operating-state result requires source results")
        if not self.node_results:
            raise ValueError("an operating-state result requires node results")
        if not self.connection_results:
            raise ValueError("an operating-state result requires connection results")

        source_by_code = {result.source_code: result for result in self.source_results}
        node_by_code = {result.node_code: result for result in self.node_results}
        connection_codes = {result.connection_code for result in self.connection_results}
        interlock_codes = {result.interlock_code for result in self.interlock_results}

        if len(source_by_code) != len(self.source_results):
            raise ValueError("source result codes must be unique")
        if len(node_by_code) != len(self.node_results):
            raise ValueError("node result codes must be unique")
        if len(connection_codes) != len(self.connection_results):
            raise ValueError("connection result codes must be unique")
        if len(interlock_codes) != len(self.interlock_results):
            raise ValueError("interlock result codes must be unique")

        active_source_codes = {
            result.source_code for result in self.source_results if result.active
        }
        if not active_source_codes:
            raise ValueError("an operating-state result requires an active source")

        for source_result in self.source_results:
            source_node = node_by_code.get(source_result.source_code)
            if source_node is None or source_node.node_type not in _SOURCE_NODE_TYPES:
                raise ValueError("every source result must reference a source node result")
            unknown_supplied_nodes = set(source_result.supplied_node_codes) - node_by_code.keys()
            if unknown_supplied_nodes:
                raise ValueError("source result references unknown supplied nodes")

        primary_results = [result for result in self.source_results if result.primary]
        if self.primary_source_code is None:
            if primary_results:
                raise ValueError("primary source result requires primary_source_code")
        else:
            primary_result = source_by_code.get(self.primary_source_code)
            if primary_result is None:
                raise ValueError("primary_source_code must reference a source result")
            if len(primary_results) != 1 or primary_results[0] is not primary_result:
                raise ValueError("primary_source_code must match exactly one primary result")

        for node_result in self.node_results:
            unknown_sources = set(node_result.supplying_source_codes) - active_source_codes
            if unknown_sources:
                raise ValueError("node result references an inactive or unknown source")
            for source_code in node_result.supplying_source_codes:
                if node_result.node_code not in source_by_code[source_code].supplied_node_codes:
                    raise ValueError("source and node supply references must be reciprocal")

        for source_result in self.source_results:
            for node_code in source_result.supplied_node_codes:
                if source_result.source_code not in node_by_code[node_code].supplying_source_codes:
                    raise ValueError("source and node supply references must be reciprocal")

        for interlock_result in self.interlock_results:
            unknown_connections = set(interlock_result.closed_connection_codes) - connection_codes
            if unknown_connections:
                raise ValueError("interlock result references unknown connections")

        warning_keys = tuple((warning.code, warning.reference_code) for warning in self.warnings)
        if len(warning_keys) != len(set(warning_keys)):
            raise ValueError("warning code and reference combinations must be unique")

        has_failed_check = any(
            result.status is SLDCheckStatus.FAIL for result in self.interlock_results
        )
        has_error = any(warning.severity is SLDWarningSeverity.ERROR for warning in self.warnings)
        expected_status = SLDResultStatus.DESIGN_CHECK_PASSED
        if has_failed_check or has_error:
            expected_status = SLDResultStatus.DESIGN_CHECK_FAILED
        elif self.warnings:
            expected_status = SLDResultStatus.REVIEW_REQUIRED

        if self.status is not expected_status:
            raise ValueError("operating-state status does not match checks and warnings")

    @property
    def enabled_node_count(self) -> int:
        """Return the number of enabled nodes."""

        return sum(result.enabled for result in self.node_results)

    @property
    def energized_node_count(self) -> int:
        """Return the number of energized nodes."""

        return sum(result.energized for result in self.node_results)

    @property
    def enabled_final_load_count(self) -> int:
        """Return the number of enabled final-load nodes."""

        return sum(
            result.enabled and result.node_type is SLDNodeType.FINAL_LOAD
            for result in self.node_results
        )

    @property
    def energized_final_load_count(self) -> int:
        """Return the number of energized final-load nodes."""

        return sum(
            result.energized and result.node_type is SLDNodeType.FINAL_LOAD
            for result in self.node_results
        )

    @property
    def final_load_supply_percent(self) -> Decimal:
        """Return enabled final-load supply coverage as a percentage."""

        if self.enabled_final_load_count == 0:
            return Decimal("100")
        return (
            Decimal(self.energized_final_load_count)
            * Decimal("100")
            / Decimal(self.enabled_final_load_count)
        )


@dataclass(frozen=True, slots=True)
class SLDNetworkResult:
    """Aggregate evaluation result for every defined network state."""

    network_code: str
    status: SLDResultStatus
    operating_state_results: tuple[SLDOperatingStateResult, ...]
    warnings: tuple[SLDEngineeringWarning, ...] = ()
    standard_reference: str | None = None

    def __post_init__(self) -> None:
        """Validate the aggregate result and derive status consistency."""

        object.__setattr__(
            self,
            "network_code",
            normalize_required_text("network_code", self.network_code),
        )
        object.__setattr__(
            self,
            "standard_reference",
            normalize_optional_text("standard_reference", self.standard_reference),
        )

        if not isinstance(self.status, SLDResultStatus):
            raise TypeError("status must be an SLDResultStatus value")
        if not isinstance(self.operating_state_results, tuple):
            raise TypeError("operating_state_results must be a tuple")
        if not self.operating_state_results:
            raise ValueError("a network result requires operating-state results")
        if not all(
            isinstance(result, SLDOperatingStateResult) for result in self.operating_state_results
        ):
            raise TypeError(
                "operating_state_results must contain only SLDOperatingStateResult records"
            )
        if not isinstance(self.warnings, tuple):
            raise TypeError("warnings must be a tuple")
        if not all(isinstance(warning, SLDEngineeringWarning) for warning in self.warnings):
            raise TypeError("warnings must contain only SLDEngineeringWarning records")

        state_codes = tuple(result.state_code for result in self.operating_state_results)
        if len(state_codes) != len(set(state_codes)):
            raise ValueError("operating-state result codes must be unique")
        if any(result.network_code != self.network_code for result in self.operating_state_results):
            raise ValueError("all operating-state results must reference the network code")

        warning_keys = tuple((warning.code, warning.reference_code) for warning in self.warnings)
        if len(warning_keys) != len(set(warning_keys)):
            raise ValueError("warning code and reference combinations must be unique")

        has_failed_state = any(
            result.status is SLDResultStatus.DESIGN_CHECK_FAILED
            for result in self.operating_state_results
        )
        has_warning_state = any(
            result.status is SLDResultStatus.REVIEW_REQUIRED
            for result in self.operating_state_results
        )
        has_error = any(warning.severity is SLDWarningSeverity.ERROR for warning in self.warnings)

        expected_status = SLDResultStatus.DESIGN_CHECK_PASSED
        if has_failed_state or has_error:
            expected_status = SLDResultStatus.DESIGN_CHECK_FAILED
        elif has_warning_state or self.warnings:
            expected_status = SLDResultStatus.REVIEW_REQUIRED

        if self.status is not expected_status:
            raise ValueError("network status does not match state results and warnings")

    @property
    def compliant_state_count(self) -> int:
        """Return the number of operating states whose design checks passed."""

        return sum(
            result.status is SLDResultStatus.DESIGN_CHECK_PASSED
            for result in self.operating_state_results
        )

    @property
    def warning_state_count(self) -> int:
        """Return the number of operating states with warnings."""

        return sum(
            result.status is SLDResultStatus.REVIEW_REQUIRED
            for result in self.operating_state_results
        )

    @property
    def non_compliant_state_count(self) -> int:
        """Return the number of operating states whose design checks failed."""

        return sum(
            result.status is SLDResultStatus.DESIGN_CHECK_FAILED
            for result in self.operating_state_results
        )


__all__ = [
    "SLDCheckStatus",
    "SLDConnectionStateResult",
    "SLDEngineeringWarning",
    "SLDInterlockResult",
    "SLDNetworkResult",
    "SLDNodeStateResult",
    "SLDOperatingStateResult",
    "SLDResultStatus",
    "SLDSourceStateResult",
    "SLDWarningCode",
    "SLDWarningSeverity",
]
