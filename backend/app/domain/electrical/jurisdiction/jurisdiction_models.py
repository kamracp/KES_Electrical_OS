"""Jurisdiction profile model.

A jurisdiction profile carries the reference conventions a project is designed under:
which tier of references governs when they conflict, the reference ambient temperatures
that installation tables are normalised to, and nominal supply defaults. Engine physics
never depends on the profile; only references, thresholds and vocabulary do.

Numeric values are stored on a profile only when an engine already relies on them or the
master reference register records the underlying standard as verified. Otherwise the field
is ``None`` and the profile is marked with a non-verified reference data status.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class JurisdictionProfile(StrEnum):
    """Jurisdictions the product can design under; the design basis selects one."""

    IN = "IN"
    IEC = "IEC"
    US = "US"
    UK = "UK"
    AU_NZ = "AU_NZ"
    EU = "EU"


class ReferenceVerificationStatus(StrEnum):
    """Verification vocabulary shared with the master reference register."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    LEGACY = "LEGACY"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    UNRESOLVED = "UNRESOLVED"


class ReferenceTier(StrEnum):
    """Tiers used to order references when they conflict within a profile."""

    STATUTORY = "STATUTORY"
    PROJECT_DESIGN_BASIS = "PROJECT_DESIGN_BASIS"
    NATIONAL = "NATIONAL"
    INTERNATIONAL = "INTERNATIONAL"
    MANUFACTURER_CERTIFIED = "MANUFACTURER_CERTIFIED"
    REFERENCE_ONLY = "REFERENCE_ONLY"


def _require_optional_non_negative(field_name: str, value: Decimal | None) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal or None")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _require_optional_positive(field_name: str, value: Decimal | None) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal or None")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


@dataclass(frozen=True, slots=True)
class JurisdictionProfileData:
    """Reference conventions for one jurisdiction profile."""

    profile: JurisdictionProfile
    display_name: str
    precedence: tuple[ReferenceTier, ...]
    reference_data_status: ReferenceVerificationStatus
    reference_ambient_air_c: Decimal | None = None
    reference_ambient_ground_c: Decimal | None = None
    nominal_lv_voltage_v: Decimal | None = None
    nominal_frequency_hz: Decimal | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate profile data."""

        if not isinstance(self.profile, JurisdictionProfile):
            raise TypeError("profile must be a JurisdictionProfile value")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must be a non-empty string")
        if not isinstance(self.reference_data_status, ReferenceVerificationStatus):
            raise TypeError("reference_data_status must be a ReferenceVerificationStatus value")
        if not self.precedence:
            raise ValueError("precedence must list at least one reference tier")
        if any(not isinstance(tier, ReferenceTier) for tier in self.precedence):
            raise TypeError("precedence must contain only ReferenceTier values")
        if len(set(self.precedence)) != len(self.precedence):
            raise ValueError("precedence must not repeat a reference tier")

        _require_optional_non_negative("reference_ambient_air_c", self.reference_ambient_air_c)
        _require_optional_non_negative(
            "reference_ambient_ground_c", self.reference_ambient_ground_c
        )
        _require_optional_positive("nominal_lv_voltage_v", self.nominal_lv_voltage_v)
        _require_optional_positive("nominal_frequency_hz", self.nominal_frequency_hz)

    @property
    def has_reference_ambient(self) -> bool:
        """Return True when both reference ambient temperatures are recorded."""

        return (
            self.reference_ambient_air_c is not None and self.reference_ambient_ground_c is not None
        )
