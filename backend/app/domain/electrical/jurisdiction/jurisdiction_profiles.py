"""Jurisdiction profile registry.

Every numeric value recorded here must be traceable: either an engine already relied on it
before profiles existed (in which case it inherits that engine's verification status), or the
master reference register lists the source standard as VERIFIED. Profiles whose conventions
are not yet traceable carry ``None`` values and an UNRESOLVED status; engines treat them as
"reference data pending" and must not invent defaults.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.electrical.jurisdiction.jurisdiction_models import (
    JurisdictionProfile,
    JurisdictionProfileData,
    ReferenceTier,
    ReferenceVerificationStatus,
)

# Precedence chain from docs/references/electrical-master-reference-register.md,
# "Precedence within a project". Profiles without a national specification layer omit
# the NATIONAL tier.
_PRECEDENCE_WITH_NATIONAL: tuple[ReferenceTier, ...] = (
    ReferenceTier.STATUTORY,
    ReferenceTier.PROJECT_DESIGN_BASIS,
    ReferenceTier.NATIONAL,
    ReferenceTier.INTERNATIONAL,
    ReferenceTier.MANUFACTURER_CERTIFIED,
    ReferenceTier.REFERENCE_ONLY,
)
_PRECEDENCE_INTERNATIONAL_ONLY: tuple[ReferenceTier, ...] = (
    ReferenceTier.STATUTORY,
    ReferenceTier.PROJECT_DESIGN_BASIS,
    ReferenceTier.INTERNATIONAL,
    ReferenceTier.MANUFACTURER_CERTIFIED,
    ReferenceTier.REFERENCE_ONLY,
)

# Reference ambient temperatures for the IEC-based profiles were already used by the cable
# engine as thresholds (air 30 degC, ground 20 degC) before this registry existed. Their
# source standard (REF-IEC-60364-5-52) is UNVERIFIED in the register, so the profiles carry
# the same status; this does not derive any derating factor.
_IEC_REFERENCE_AMBIENT_AIR_C = Decimal("30")
_IEC_REFERENCE_AMBIENT_GROUND_C = Decimal("20")

PROFILES: dict[JurisdictionProfile, JurisdictionProfileData] = {
    JurisdictionProfile.IN: JurisdictionProfileData(
        profile=JurisdictionProfile.IN,
        display_name="India (CEA Regulations, IS, CPWD)",
        precedence=_PRECEDENCE_WITH_NATIONAL,
        reference_data_status=ReferenceVerificationStatus.UNVERIFIED,
        reference_ambient_air_c=_IEC_REFERENCE_AMBIENT_AIR_C,
        reference_ambient_ground_c=_IEC_REFERENCE_AMBIENT_GROUND_C,
        nominal_lv_voltage_v=Decimal("415"),
        nominal_frequency_hz=Decimal("50"),
        notes=(
            "National tier: CPWD General Specifications (REF-CPWD-P1-2023 with amendments, "
            "REF-CPWD-P2-2023 VERIFIED) and IS standards; ambient conventions inherited from "
            "the cable engine thresholds pending IEC 60364-5-52 verification."
        ),
    ),
    JurisdictionProfile.IEC: JurisdictionProfileData(
        profile=JurisdictionProfile.IEC,
        display_name="IEC (international, no national layer)",
        precedence=_PRECEDENCE_INTERNATIONAL_ONLY,
        reference_data_status=ReferenceVerificationStatus.UNVERIFIED,
        reference_ambient_air_c=_IEC_REFERENCE_AMBIENT_AIR_C,
        reference_ambient_ground_c=_IEC_REFERENCE_AMBIENT_GROUND_C,
        nominal_lv_voltage_v=Decimal("400"),
        nominal_frequency_hz=Decimal("50"),
        notes="Ambient conventions inherited from the cable engine thresholds.",
    ),
    JurisdictionProfile.UK: JurisdictionProfileData(
        profile=JurisdictionProfile.UK,
        display_name="United Kingdom (BS 7671 wiring regulations)",
        precedence=_PRECEDENCE_WITH_NATIONAL,
        reference_data_status=ReferenceVerificationStatus.UNRESOLVED,
        notes="National references not yet registered; reference data pending.",
    ),
    JurisdictionProfile.EU: JurisdictionProfileData(
        profile=JurisdictionProfile.EU,
        display_name="European Union (CENELEC HD 60364 series)",
        precedence=_PRECEDENCE_WITH_NATIONAL,
        reference_data_status=ReferenceVerificationStatus.UNRESOLVED,
        notes="Harmonised documents not yet registered; reference data pending.",
    ),
    JurisdictionProfile.US: JurisdictionProfileData(
        profile=JurisdictionProfile.US,
        display_name="United States (NEC / NFPA 70)",
        precedence=_PRECEDENCE_WITH_NATIONAL,
        reference_data_status=ReferenceVerificationStatus.UNRESOLVED,
        notes="NEC-based conventions differ from IEC; nothing recorded until registered.",
    ),
    JurisdictionProfile.AU_NZ: JurisdictionProfileData(
        profile=JurisdictionProfile.AU_NZ,
        display_name="Australia / New Zealand (AS/NZS 3000 series)",
        precedence=_PRECEDENCE_WITH_NATIONAL,
        reference_data_status=ReferenceVerificationStatus.UNRESOLVED,
        notes="National references not yet registered; reference data pending.",
    ),
}

DEFAULT_PROFILE = JurisdictionProfile.IN


def get_profile(profile: JurisdictionProfile) -> JurisdictionProfileData:
    """Return the registry entry for ``profile``; every enum member is registered."""

    if not isinstance(profile, JurisdictionProfile):
        raise TypeError("profile must be a JurisdictionProfile value")
    return PROFILES[profile]
