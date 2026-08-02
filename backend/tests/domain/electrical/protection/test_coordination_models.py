"""
Unit tests for protection coordination domain models.
KESE-S2-M11 Phase-2
"""

from decimal import Decimal

import pytest

from app.domain.electrical.protection.coordination_models import (
    CoordinationCatalogueEntry,
    CoordinationDeviceReference,
    CoordinationObjective,
    CoordinationStudyInput,
    CoordinationVerificationStatus,
    StarterMethod,
)


def make_device(
    code: str = "ACB-UP-01",
) -> CoordinationDeviceReference:
    return CoordinationDeviceReference(
        code=code,
        family="Master Range",
        manufacturer="Schneider Electric",
        device_type="ACB",
        rated_current_a=Decimal("1600"),
        breaking_capacity_ka=Decimal("65"),
    )


def make_entry() -> CoordinationCatalogueEntry:
    return CoordinationCatalogueEntry(
        code="SEL-001",
        objective=CoordinationObjective.SELECTIVITY,
        verification_status=(
            CoordinationVerificationStatus.VERIFIED
        ),
        upstream_device=make_device(),
        downstream_device=make_device("MCCB-DN-01"),
        maximum_selective_current_ka=Decimal("35"),
        manufacturer_document="Selectivity Table",
    )


@pytest.mark.unit
def test_create_device_reference() -> None:
    device = make_device()

    assert device.code == "ACB-UP-01"
    assert device.rated_current_a == Decimal("1600")


@pytest.mark.unit
def test_create_selectivity_entry() -> None:
    entry = make_entry()

    assert entry.objective is CoordinationObjective.SELECTIVITY
    assert entry.maximum_selective_current_ka == Decimal("35")


@pytest.mark.unit
def test_create_coordination_study() -> None:
    study = CoordinationStudyInput(
        code="STUDY-001",
        name="Main PCC Study",
        objective=CoordinationObjective.SELECTIVITY,
        prospective_fault_current_ka=Decimal("30"),
        upstream_device=make_device(),
        downstream_device=make_device("MCCB-DN-01"),
        catalogue_entries=(make_entry(),),
    )

    assert study.code == "STUDY-001"
    assert len(study.catalogue_entries) == 1


@pytest.mark.unit
def test_selectivity_requires_limit() -> None:
    with pytest.raises(
        ValueError,
        match="maximum_selective_current_ka",
    ):
        CoordinationCatalogueEntry(
            code="SEL-BAD",
            objective=CoordinationObjective.SELECTIVITY,
            verification_status=(
                CoordinationVerificationStatus.UNVERIFIED
            ),
            upstream_device=make_device(),
            downstream_device=make_device("MCCB-DN-01"),
        )


@pytest.mark.unit
def test_verified_entry_requires_document() -> None:
    with pytest.raises(
        ValueError,
        match="manufacturer_document",
    ):
        CoordinationCatalogueEntry(
            code="SEL-BAD-02",
            objective=CoordinationObjective.SELECTIVITY,
            verification_status=(
                CoordinationVerificationStatus.VERIFIED
            ),
            upstream_device=make_device(),
            downstream_device=make_device("MCCB-DN-01"),
            maximum_selective_current_ka=Decimal("35"),
        )


@pytest.mark.unit
def test_duplicate_catalogue_codes_are_rejected() -> None:
    entry = make_entry()

    with pytest.raises(
        ValueError,
        match="catalogue entry codes",
    ):
        CoordinationStudyInput(
            code="STUDY-DUP",
            name="Duplicate Entry Study",
            objective=CoordinationObjective.SELECTIVITY,
            prospective_fault_current_ka=Decimal("30"),
            upstream_device=make_device(),
            downstream_device=make_device("MCCB-DN-01"),
            catalogue_entries=(entry, entry),
        )


@pytest.mark.unit
def test_type_2_study_requires_motor_data() -> None:
    type_2_entry = CoordinationCatalogueEntry(
        code="T2-001",
        objective=CoordinationObjective.TYPE_2,
        verification_status=(
            CoordinationVerificationStatus.VERIFIED
        ),
        upstream_device=make_device(),
        downstream_device=make_device("MPCB-DN-01"),
        starter_method=StarterMethod.DOL,
        motor_power_kw=Decimal("45"),
        manufacturer_document="Type-2 Table",
    )

    with pytest.raises(
        ValueError,
        match="required_motor_power_kw",
    ):
        CoordinationStudyInput(
            code="STUDY-T2",
            name="Type-2 Study",
            objective=CoordinationObjective.TYPE_2,
            prospective_fault_current_ka=Decimal("30"),
            upstream_device=make_device(),
            downstream_device=make_device("MPCB-DN-01"),
            catalogue_entries=(type_2_entry,),
            required_starter_method=StarterMethod.DOL,
        )
