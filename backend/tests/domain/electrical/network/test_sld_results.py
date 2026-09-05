"""
Unit tests for source-integration and SLD evaluation results.
KESE-S2-M14
"""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.domain.electrical.network.sld_models import OperatingMode, SLDNodeType
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


def make_warning(**overrides: object) -> SLDEngineeringWarning:
    values: dict[str, object] = {
        "code": SLDWarningCode.FINAL_LOAD_UNSUPPLIED,
        "severity": SLDWarningSeverity.WARNING,
        "message": "Final load is not supplied",
        "reference_code": "LOAD-01",
    }
    values.update(overrides)
    return SLDEngineeringWarning(**values)


def make_source(**overrides: object) -> SLDSourceStateResult:
    values: dict[str, object] = {
        "source_code": "UTILITY-01",
        "priority": 1,
        "active": True,
        "primary": True,
        "supplied_node_codes": ("UTILITY-01", "LOAD-01"),
    }
    values.update(overrides)
    return SLDSourceStateResult(**values)


def make_node(**overrides: object) -> SLDNodeStateResult:
    values: dict[str, object] = {
        "node_code": "UTILITY-01",
        "node_type": SLDNodeType.UTILITY_GRID,
        "enabled": True,
        "energized": True,
        "isolated": False,
        "supplying_source_codes": ("UTILITY-01",),
    }
    values.update(overrides)
    return SLDNodeStateResult(**values)


def make_connection(**overrides: object) -> SLDConnectionStateResult:
    values: dict[str, object] = {
        "connection_code": "GRID-LOAD",
        "closed": True,
        "energized": True,
        "from_node_energized": True,
        "to_node_energized": True,
    }
    values.update(overrides)
    return SLDConnectionStateResult(**values)


def make_interlock(**overrides: object) -> SLDInterlockResult:
    values: dict[str, object] = {
        "interlock_code": "IL-INCOMERS",
        "closed_connection_codes": ("GRID-LOAD",),
        "maximum_simultaneously_closed": 1,
        "status": SLDCheckStatus.PASS,
    }
    values.update(overrides)
    return SLDInterlockResult(**values)


def make_state(**overrides: object) -> SLDOperatingStateResult:
    source = make_source()
    nodes = (
        make_node(),
        make_node(
            node_code="LOAD-01",
            node_type=SLDNodeType.FINAL_LOAD,
        ),
    )
    values: dict[str, object] = {
        "network_code": "SLD-01",
        "state_code": "STATE-NORMAL",
        "mode": OperatingMode.NORMAL,
        "status": SLDResultStatus.DESIGN_CHECK_PASSED,
        "primary_source_code": "UTILITY-01",
        "source_results": (source,),
        "node_results": nodes,
        "connection_results": (make_connection(),),
        "interlock_results": (make_interlock(),),
        "warnings": (),
    }
    values.update(overrides)
    return SLDOperatingStateResult(**values)


def make_warning_state(**overrides: object) -> SLDOperatingStateResult:
    source = make_source(supplied_node_codes=("UTILITY-01",))
    nodes = (
        make_node(),
        make_node(
            node_code="LOAD-01",
            node_type=SLDNodeType.FINAL_LOAD,
            energized=False,
            supplying_source_codes=(),
        ),
    )
    values: dict[str, object] = {
        "state_code": "STATE-MAINTENANCE",
        "mode": OperatingMode.MAINTENANCE,
        "status": SLDResultStatus.REVIEW_REQUIRED,
        "source_results": (source,),
        "node_results": nodes,
        "connection_results": (make_connection(to_node_energized=False),),
        "warnings": (make_warning(),),
    }
    values.update(overrides)
    return make_state(**values)


def make_network(**overrides: object) -> SLDNetworkResult:
    values: dict[str, object] = {
        "network_code": "SLD-01",
        "status": SLDResultStatus.DESIGN_CHECK_PASSED,
        "operating_state_results": (make_state(),),
        "warnings": (),
        "standard_reference": "IEC 60364",
    }
    values.update(overrides)
    return SLDNetworkResult(**values)


@pytest.mark.unit
def test_create_valid_engineering_warning() -> None:
    warning = make_warning(
        message="  Final load is not supplied  ",
        reference_code="  LOAD-01  ",
    )

    assert warning.message == "Final load is not supplied"
    assert warning.reference_code == "LOAD-01"


@pytest.mark.unit
def test_engineering_warning_is_immutable() -> None:
    warning = make_warning()

    with pytest.raises(FrozenInstanceError):
        warning.message = "Changed"


@pytest.mark.unit
def test_engineering_warning_rejects_invalid_enum_values() -> None:
    with pytest.raises(TypeError, match="SLDWarningCode"):
        make_warning(code="FINAL_LOAD_UNSUPPLIED")

    with pytest.raises(TypeError, match="SLDWarningSeverity"):
        make_warning(severity="WARNING")


@pytest.mark.unit
def test_create_valid_source_state() -> None:
    source = make_source(source_code="  UTILITY-01  ")

    assert source.source_code == "UTILITY-01"
    assert source.priority == 1
    assert source.primary is True


@pytest.mark.unit
def test_primary_source_must_be_active() -> None:
    with pytest.raises(ValueError, match="primary source must be active"):
        make_source(active=False)


@pytest.mark.unit
def test_inactive_source_cannot_supply_nodes() -> None:
    with pytest.raises(ValueError, match="inactive source cannot supply"):
        make_source(active=False, primary=False)


@pytest.mark.unit
def test_source_supplied_node_codes_must_be_unique() -> None:
    with pytest.raises(ValueError, match="supplied_node_codes values must be unique"):
        make_source(supplied_node_codes=("LOAD-01", "LOAD-01"))


@pytest.mark.unit
def test_create_valid_node_state() -> None:
    node = make_node(node_code="  UTILITY-01  ")

    assert node.node_code == "UTILITY-01"
    assert node.energized is True


@pytest.mark.unit
def test_node_state_rejects_invalid_node_type() -> None:
    with pytest.raises(TypeError, match="SLDNodeType"):
        make_node(node_type="UTILITY_GRID")


@pytest.mark.unit
def test_isolated_node_cannot_be_energized() -> None:
    with pytest.raises(ValueError, match="isolated node cannot be energized"):
        make_node(isolated=True)


@pytest.mark.unit
def test_disabled_node_cannot_be_energized() -> None:
    with pytest.raises(ValueError, match="disabled node cannot be energized"):
        make_node(enabled=False)


@pytest.mark.unit
def test_energized_node_requires_supplying_source() -> None:
    with pytest.raises(ValueError, match="requires at least one supplying source"):
        make_node(supplying_source_codes=())


@pytest.mark.unit
def test_deenergized_node_rejects_supplying_source() -> None:
    with pytest.raises(ValueError, match="de-energized node cannot have"):
        make_node(energized=False)


@pytest.mark.unit
def test_connection_state_must_match_switch_and_endpoints() -> None:
    with pytest.raises(ValueError, match="must match its closed and endpoint states"):
        make_connection(closed=False)

    with pytest.raises(ValueError, match="must match its closed and endpoint states"):
        make_connection(
            energized=False,
            from_node_energized=True,
            to_node_energized=False,
        )


@pytest.mark.unit
def test_valid_deenergized_connection() -> None:
    connection = make_connection(
        closed=True,
        energized=False,
        from_node_energized=False,
        to_node_energized=False,
    )

    assert connection.energized is False


@pytest.mark.unit
def test_create_pass_and_fail_interlock_results() -> None:
    passing = make_interlock()
    failing = make_interlock(
        closed_connection_codes=("INCOMER-A", "INCOMER-B"),
        status=SLDCheckStatus.FAIL,
    )

    assert passing.status is SLDCheckStatus.PASS
    assert failing.status is SLDCheckStatus.FAIL


@pytest.mark.unit
def test_interlock_status_must_match_closed_count() -> None:
    with pytest.raises(ValueError, match="does not match the closed connection count"):
        make_interlock(status=SLDCheckStatus.FAIL)


@pytest.mark.unit
def test_create_valid_operating_state_result() -> None:
    state = make_state()

    assert state.enabled_node_count == 2
    assert state.energized_node_count == 2
    assert state.enabled_final_load_count == 1
    assert state.energized_final_load_count == 1
    assert state.final_load_supply_percent == Decimal("100")


@pytest.mark.unit
def test_warning_state_reports_zero_load_supply() -> None:
    state = make_warning_state()

    assert state.status is SLDResultStatus.REVIEW_REQUIRED
    assert state.energized_final_load_count == 0
    assert state.final_load_supply_percent == Decimal("0")


@pytest.mark.unit
def test_operating_state_requires_active_source() -> None:
    inactive_source = make_source(
        active=False,
        primary=False,
        supplied_node_codes=(),
    )

    with pytest.raises(ValueError, match="requires an active source"):
        make_state(
            primary_source_code=None,
            source_results=(inactive_source,),
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field_name", "duplicate_value", "message"),
    (
        ("source_results", make_source(), "source result codes must be unique"),
        ("node_results", make_node(), "node result codes must be unique"),
        (
            "connection_results",
            make_connection(),
            "connection result codes must be unique",
        ),
        ("interlock_results", make_interlock(), "interlock result codes must be unique"),
    ),
)
def test_operating_state_result_codes_must_be_unique(
    field_name: str,
    duplicate_value: object,
    message: str,
) -> None:
    state = make_state()
    existing_records = getattr(state, field_name)

    with pytest.raises(ValueError, match=message):
        make_state(**{field_name: (*existing_records, duplicate_value)})


@pytest.mark.unit
def test_primary_source_code_must_match_primary_result() -> None:
    with pytest.raises(ValueError, match="must reference a source result"):
        make_state(primary_source_code="UNKNOWN")

    with pytest.raises(ValueError, match="match exactly one primary result"):
        make_state(
            source_results=(make_source(primary=False),),
        )


@pytest.mark.unit
def test_source_result_must_reference_source_node() -> None:
    with pytest.raises(ValueError, match="must reference a source node result"):
        make_state(
            source_results=(
                make_source(
                    source_code="UNKNOWN-SOURCE",
                    supplied_node_codes=(),
                ),
            ),
            primary_source_code="UNKNOWN-SOURCE",
        )


@pytest.mark.unit
def test_source_result_rejects_unknown_supplied_node() -> None:
    with pytest.raises(ValueError, match="unknown supplied nodes"):
        make_state(
            source_results=(
                make_source(
                    supplied_node_codes=("UTILITY-01", "LOAD-01", "UNKNOWN"),
                ),
            ),
        )


@pytest.mark.unit
def test_node_result_rejects_inactive_or_unknown_source() -> None:
    nodes = (
        make_node(supplying_source_codes=("UNKNOWN",)),
        make_node(
            node_code="LOAD-01",
            node_type=SLDNodeType.FINAL_LOAD,
        ),
    )

    with pytest.raises(ValueError, match="inactive or unknown source"):
        make_state(node_results=nodes)


@pytest.mark.unit
def test_source_and_node_supply_references_must_be_reciprocal() -> None:
    source = make_source(supplied_node_codes=("UTILITY-01",))

    with pytest.raises(ValueError, match="must be reciprocal"):
        make_state(source_results=(source,))


@pytest.mark.unit
def test_interlock_result_rejects_unknown_connection() -> None:
    interlock = make_interlock(closed_connection_codes=("UNKNOWN",))

    with pytest.raises(ValueError, match="references unknown connections"):
        make_state(interlock_results=(interlock,))


@pytest.mark.unit
def test_warning_reference_combinations_must_be_unique() -> None:
    warning = make_warning()

    with pytest.raises(ValueError, match="combinations must be unique"):
        make_state(
            status=SLDResultStatus.REVIEW_REQUIRED,
            warnings=(warning, warning),
        )


@pytest.mark.unit
def test_operating_state_status_must_match_warning_severity() -> None:
    with pytest.raises(ValueError, match="status does not match"):
        make_state(
            status=SLDResultStatus.DESIGN_CHECK_PASSED,
            warnings=(make_warning(),),
        )

    error = make_warning(severity=SLDWarningSeverity.ERROR)
    state = make_state(
        status=SLDResultStatus.DESIGN_CHECK_FAILED,
        warnings=(error,),
    )

    assert state.status is SLDResultStatus.DESIGN_CHECK_FAILED


@pytest.mark.unit
def test_failed_interlock_requires_failed_design_check_state() -> None:
    connections = (
        make_connection(connection_code="INCOMER-A"),
        make_connection(connection_code="INCOMER-B"),
    )
    failed_interlock = make_interlock(
        closed_connection_codes=("INCOMER-A", "INCOMER-B"),
        status=SLDCheckStatus.FAIL,
    )
    state = make_state(
        status=SLDResultStatus.DESIGN_CHECK_FAILED,
        connection_results=connections,
        interlock_results=(failed_interlock,),
    )

    assert state.status is SLDResultStatus.DESIGN_CHECK_FAILED


@pytest.mark.unit
def test_create_valid_network_result() -> None:
    result = make_network()

    assert result.status is SLDResultStatus.DESIGN_CHECK_PASSED
    assert result.compliant_state_count == 1
    assert result.warning_state_count == 0
    assert result.non_compliant_state_count == 0
    assert result.standard_reference == "IEC 60364"


@pytest.mark.unit
def test_network_operating_state_codes_must_be_unique() -> None:
    state = make_state()

    with pytest.raises(ValueError, match="result codes must be unique"):
        make_network(operating_state_results=(state, state))


@pytest.mark.unit
def test_network_states_must_reference_same_network() -> None:
    state = make_state(network_code="OTHER-SLD")

    with pytest.raises(ValueError, match="must reference the network code"):
        make_network(operating_state_results=(state,))


@pytest.mark.unit
def test_network_status_aggregates_operating_states() -> None:
    warning_state = make_warning_state()
    result = make_network(
        status=SLDResultStatus.REVIEW_REQUIRED,
        operating_state_results=(make_state(), warning_state),
    )

    assert result.compliant_state_count == 1
    assert result.warning_state_count == 1


@pytest.mark.unit
def test_network_status_must_match_results_and_warnings() -> None:
    with pytest.raises(ValueError, match="network status does not match"):
        make_network(
            status=SLDResultStatus.DESIGN_CHECK_PASSED,
            warnings=(make_warning(),),
        )


@pytest.mark.unit
def test_network_warning_reference_combinations_must_be_unique() -> None:
    warning = make_warning()

    with pytest.raises(ValueError, match="combinations must be unique"):
        make_network(
            status=SLDResultStatus.REVIEW_REQUIRED,
            warnings=(warning, warning),
        )
