"""
Unit tests for protection relay and TCC domain models.
KESE-S2-M12
"""

from decimal import Decimal

import pytest

from app.domain.electrical.relay.relay_models import (
    CTConnection,
    CurrentTransformerInput,
    ProtectionRelayInput,
    RelayCoordinationStudyInput,
    RelayCurveFamily,
    RelayCurveInput,
    RelayFunction,
    RelayPickupSettings,
    RelayRole,
)


def make_ct(
    **overrides: object,
) -> CurrentTransformerInput:
    values: dict[str, object] = {
        "primary_current_a": Decimal("800"),
        "secondary_current_a": Decimal("1"),
        "burden_va": Decimal("15"),
        "accuracy_class": "5P20",
        "connection": CTConnection.STAR,
    }

    values.update(overrides)

    return CurrentTransformerInput(**values)


def make_settings(
    **overrides: object,
) -> RelayPickupSettings:
    values: dict[str, object] = {
        "pickup_current_a": Decimal("800"),
        "time_multiplier": Decimal("0.20"),
        "instantaneous_pickup_a": Decimal("8000"),
        "instantaneous_delay_s": Decimal("0"),
        "reset_ratio": Decimal("0.95"),
    }

    values.update(overrides)

    return RelayPickupSettings(**values)


def make_curve(
    **overrides: object,
) -> RelayCurveInput:
    values: dict[str, object] = {
        "family": RelayCurveFamily.IEC_STANDARD_INVERSE,
        "settings": make_settings(),
        "minimum_operating_time_s": Decimal("0"),
        "maximum_operating_time_s": Decimal("10"),
        "manufacturer_curve_code": "IEC-SI",
        "reference_document": "IEC 60255",
    }

    values.update(overrides)

    return RelayCurveInput(**values)


def make_relay(
    *,
    code: str = "RLY-DN-01",
    role: RelayRole = RelayRole.DOWNSTREAM,
    **overrides: object,
) -> ProtectionRelayInput:
    values: dict[str, object] = {
        "code": code,
        "name": "Downstream Overcurrent Relay",
        "function": RelayFunction.PHASE_OVERCURRENT,
        "role": role,
        "ct": make_ct(),
        "curve": make_curve(),
        "protected_equipment_code": "FDR-01",
        "breaker_code": "VCB-01",
        "grading_margin_s": Decimal("0.30"),
        "coordination_group": "GROUP-01",
        "manufacturer": "Manufacturer Neutral",
        "model": "OC-Relay",
        "standard_reference": "IEC 60255",
    }

    values.update(overrides)

    return ProtectionRelayInput(**values)


@pytest.mark.unit
def test_create_valid_current_transformer() -> None:
    ct = make_ct()

    assert ct.primary_current_a == Decimal("800")
    assert ct.secondary_current_a == Decimal("1")
    assert ct.ratio == Decimal("800")
    assert ct.connection is CTConnection.STAR


@pytest.mark.unit
def test_ct_text_is_trimmed() -> None:
    ct = make_ct(
        accuracy_class="  5P20  ",
    )

    assert ct.accuracy_class == "5P20"


@pytest.mark.unit
def test_invalid_ct_secondary_current_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must be 1 A or 5 A",
    ):
        make_ct(
            secondary_current_a=Decimal("2"),
        )


@pytest.mark.unit
def test_create_valid_relay_pickup_settings() -> None:
    settings = make_settings()

    assert settings.pickup_current_a == Decimal("800")
    assert settings.time_multiplier == Decimal("0.20")
    assert settings.reset_ratio == Decimal("0.95")


@pytest.mark.unit
def test_reset_ratio_above_one_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="reset_ratio must not exceed 1",
    ):
        make_settings(
            reset_ratio=Decimal("1.01"),
        )


@pytest.mark.unit
def test_instantaneous_delay_requires_pickup() -> None:
    with pytest.raises(
        ValueError,
        match="instantaneous_delay_s requires",
    ):
        make_settings(
            instantaneous_pickup_a=None,
            instantaneous_delay_s=Decimal("0.05"),
        )


@pytest.mark.unit
def test_create_valid_inverse_curve() -> None:
    curve = make_curve()

    assert curve.family is RelayCurveFamily.IEC_STANDARD_INVERSE
    assert curve.settings.pickup_current_a == Decimal("800")
    assert curve.manufacturer_curve_code == "IEC-SI"


@pytest.mark.unit
def test_definite_time_curve_requires_delay() -> None:
    with pytest.raises(
        ValueError,
        match="DEFINITE_TIME curve requires",
    ):
        make_curve(
            family=RelayCurveFamily.DEFINITE_TIME,
            settings=make_settings(
                definite_time_delay_s=None,
            ),
        )


@pytest.mark.unit
def test_maximum_operating_time_cannot_be_below_minimum() -> None:
    with pytest.raises(
        ValueError,
        match="must not be below minimum_operating_time_s",
    ):
        make_curve(
            minimum_operating_time_s=Decimal("2"),
            maximum_operating_time_s=Decimal("1"),
        )


@pytest.mark.unit
def test_create_valid_protection_relay() -> None:
    relay = make_relay()

    assert relay.code == "RLY-DN-01"
    assert relay.function is RelayFunction.PHASE_OVERCURRENT
    assert relay.role is RelayRole.DOWNSTREAM
    assert relay.ct.ratio == Decimal("800")


@pytest.mark.unit
def test_relay_text_is_trimmed() -> None:
    relay = make_relay(
        code="  RLY-DN-01  ",
        name="  Downstream Relay  ",
        protected_equipment_code="  FDR-01  ",
        notes="  Approved  ",
    )

    assert relay.code == "RLY-DN-01"
    assert relay.name == "Downstream Relay"
    assert relay.protected_equipment_code == "FDR-01"
    assert relay.notes == "Approved"


@pytest.mark.unit
def test_create_valid_coordination_study() -> None:
    downstream = make_relay(
        code="RLY-DN-01",
        role=RelayRole.DOWNSTREAM,
    )
    upstream = make_relay(
        code="RLY-UP-01",
        role=RelayRole.UPSTREAM,
    )

    study = RelayCoordinationStudyInput(
        code="TCC-001",
        name="Main Feeder Relay Coordination",
        fault_current_a=Decimal("10000"),
        relays=(downstream, upstream),
        minimum_grading_margin_s=Decimal("0.30"),
        maximum_operating_time_s=Decimal("2"),
        standard_reference="IEC 60255",
    )

    assert study.code == "TCC-001"
    assert len(study.relays) == 2
    assert study.fault_current_a == Decimal("10000")


@pytest.mark.unit
def test_coordination_study_requires_two_relays() -> None:
    with pytest.raises(
        ValueError,
        match="requires at least two relays",
    ):
        RelayCoordinationStudyInput(
            code="TCC-001",
            name="Incomplete Coordination Study",
            fault_current_a=Decimal("10000"),
            relays=(make_relay(),),
        )


@pytest.mark.unit
def test_duplicate_relay_codes_are_rejected() -> None:
    relay = make_relay()

    with pytest.raises(
        ValueError,
        match="relay codes must be unique",
    ):
        RelayCoordinationStudyInput(
            code="TCC-001",
            name="Duplicate Relay Study",
            fault_current_a=Decimal("10000"),
            relays=(relay, relay),
        )
