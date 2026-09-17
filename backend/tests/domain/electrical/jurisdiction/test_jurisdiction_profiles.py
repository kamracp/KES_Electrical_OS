"""Tests for jurisdiction profile model and registry rules."""

from decimal import Decimal

import pytest

from app.domain.electrical.jurisdiction import (
    FaultGoverningReferences,
    GoverningReferences,
    JurisdictionProfile,
    JurisdictionProfileData,
    ReferenceTier,
    ReferenceVerificationStatus,
)
from app.domain.electrical.jurisdiction.jurisdiction_profiles import (
    DEFAULT_PROFILE,
    PROFILES,
    get_profile,
)


def make_profile(**overrides: object) -> JurisdictionProfileData:
    values: dict[str, object] = {
        "profile": JurisdictionProfile.IEC,
        "display_name": "Test profile",
        "precedence": (ReferenceTier.STATUTORY, ReferenceTier.INTERNATIONAL),
        "reference_data_status": ReferenceVerificationStatus.UNVERIFIED,
    }
    values.update(overrides)
    return JurisdictionProfileData(**values)


@pytest.mark.unit
def test_registry_covers_every_profile_exactly_once() -> None:
    assert set(PROFILES) == set(JurisdictionProfile)
    for profile, data in PROFILES.items():
        assert data.profile is profile


@pytest.mark.unit
def test_default_profile_is_india_and_registered() -> None:
    assert DEFAULT_PROFILE is JurisdictionProfile.IN
    assert get_profile(DEFAULT_PROFILE).profile is JurisdictionProfile.IN


@pytest.mark.unit
def test_get_profile_rejects_non_enum_values() -> None:
    with pytest.raises(TypeError):
        get_profile("IN")  # type: ignore[arg-type]


@pytest.mark.unit
def test_unresolved_profiles_record_no_numeric_conventions() -> None:
    for data in PROFILES.values():
        if data.reference_data_status is ReferenceVerificationStatus.UNRESOLVED:
            assert data.reference_ambient_air_c is None
            assert data.reference_ambient_ground_c is None
            assert data.nominal_lv_voltage_v is None
            assert data.nominal_frequency_hz is None
            assert not data.has_reference_ambient


@pytest.mark.unit
def test_profiles_with_ambient_conventions_are_not_unresolved() -> None:
    for data in PROFILES.values():
        if data.has_reference_ambient:
            assert data.reference_data_status is not ReferenceVerificationStatus.UNRESOLVED


@pytest.mark.unit
def test_iec_based_profiles_share_engine_reference_ambient() -> None:
    for profile in (JurisdictionProfile.IN, JurisdictionProfile.IEC):
        data = get_profile(profile)
        assert data.reference_ambient_air_c == Decimal("30")
        assert data.reference_ambient_ground_c == Decimal("20")
        assert data.has_reference_ambient


@pytest.mark.unit
def test_every_precedence_chain_starts_with_statutory_and_ends_with_reference_only() -> None:
    for data in PROFILES.values():
        assert data.precedence[0] is ReferenceTier.STATUTORY
        assert data.precedence[-1] is ReferenceTier.REFERENCE_ONLY
        assert len(set(data.precedence)) == len(data.precedence)


@pytest.mark.unit
def test_profile_data_rejects_empty_or_repeated_precedence() -> None:
    with pytest.raises(ValueError):
        make_profile(precedence=())
    with pytest.raises(ValueError):
        make_profile(precedence=(ReferenceTier.STATUTORY, ReferenceTier.STATUTORY))


@pytest.mark.unit
def test_profile_data_rejects_invalid_numeric_conventions() -> None:
    with pytest.raises(ValueError):
        make_profile(reference_ambient_air_c=Decimal("-1"))
    with pytest.raises(ValueError):
        make_profile(nominal_frequency_hz=Decimal("0"))
    with pytest.raises(TypeError):
        make_profile(nominal_lv_voltage_v=415)  # type: ignore[arg-type]


@pytest.mark.unit
def test_profile_data_rejects_blank_display_name_and_wrong_enum_types() -> None:
    with pytest.raises(ValueError):
        make_profile(display_name="  ")
    with pytest.raises(TypeError):
        make_profile(profile="IN")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        make_profile(reference_data_status="VERIFIED")  # type: ignore[arg-type]


@pytest.mark.unit
def test_governing_references_default_to_none() -> None:
    profile = make_profile()
    assert profile.governing_references is None
    assert profile.has_governing_references is False


@pytest.mark.unit
@pytest.mark.parametrize("field_name", ["sizing_reference", "ampacity_reference"])
def test_governing_references_reject_blank_text(field_name: str) -> None:
    values = {"sizing_reference": "IEC 60364-5-52", "ampacity_reference": "IEC 60287"}
    values[field_name] = "   "
    with pytest.raises(ValueError, match=field_name):
        GoverningReferences(**values)


@pytest.mark.unit
def test_profile_rejects_wrong_governing_references_type() -> None:
    with pytest.raises(TypeError, match="governing_references"):
        make_profile(governing_references="IEC 60364-5-52")  # type: ignore[arg-type]


@pytest.mark.unit
@pytest.mark.parametrize("profile", [JurisdictionProfile.IN, JurisdictionProfile.IEC])
def test_iec_based_profiles_carry_iec_governing_references(
    profile: JurisdictionProfile,
) -> None:
    data = get_profile(profile)
    assert data.has_governing_references is True
    assert data.governing_references == GoverningReferences(
        sizing_reference="IEC 60364-5-52",
        ampacity_reference="IEC 60287",
    )


@pytest.mark.unit
def test_unresolved_profiles_carry_no_governing_references() -> None:
    unresolved = [
        data
        for data in PROFILES.values()
        if data.reference_data_status is ReferenceVerificationStatus.UNRESOLVED
    ]
    assert unresolved, "registry must contain unresolved profiles for this rule to bite"
    for data in unresolved:
        assert data.governing_references is None, data.profile
        assert data.has_governing_references is False, data.profile


@pytest.mark.unit
@pytest.mark.parametrize("field_name", ["short_circuit_reference", "earth_current_reference"])
def test_fault_governing_references_reject_blank_text(field_name: str) -> None:
    values = {"short_circuit_reference": "IEC 60909-0", "earth_current_reference": "IEC 60909-3"}
    values[field_name] = ""
    with pytest.raises(ValueError, match=field_name):
        FaultGoverningReferences(**values)


@pytest.mark.unit
@pytest.mark.parametrize("profile", [JurisdictionProfile.IN, JurisdictionProfile.IEC])
def test_iec_based_profiles_carry_fault_references_without_edition_years(
    profile: JurisdictionProfile,
) -> None:
    data = get_profile(profile)
    assert data.has_fault_governing_references is True
    assert data.fault_governing_references == FaultGoverningReferences(
        short_circuit_reference="IEC 60909-0",
        earth_current_reference="IEC 60909-3",
    )


@pytest.mark.unit
def test_unresolved_profiles_carry_no_fault_governing_references() -> None:
    for data in PROFILES.values():
        if data.reference_data_status is ReferenceVerificationStatus.UNRESOLVED:
            assert data.fault_governing_references is None, data.profile
            assert data.has_fault_governing_references is False, data.profile
