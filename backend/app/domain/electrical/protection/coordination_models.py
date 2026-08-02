
"""
Domain models for protection coordination studies.
KESE-S2-M11 Phase-2
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.electrical.sources.common import (
    normalize_optional_text,
    normalize_required_text,
    require_positive_decimal,
)


class CoordinationObjective(StrEnum):
    """Required protection coordination objective."""

    SELECTIVITY = "SELECTIVITY"
    CASCADING = "CASCADING"
    TYPE_1 = "TYPE_1"
    TYPE_2 = "TYPE_2"


class CoordinationVerificationStatus(StrEnum):
    """Catalogue verification state."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    ENGINEERING_REVIEW = "ENGINEERING_REVIEW"


class StarterMethod(StrEnum):
    """Motor starting method."""

    DOL = "DOL"
    STAR_DELTA = "STAR_DELTA"
    SOFT_STARTER = "SOFT_STARTER"
    VFD = "VFD"


@dataclass(frozen=True, slots=True)
class CoordinationDeviceReference:
    """Reference to one coordinated protection device."""

    code: str
    family: str
    manufacturer: str
    device_type: str

    rated_current_a: Decimal
    breaking_capacity_ka: Decimal

    trip_unit: str | None = None
    role: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            normalize_required_text("code", self.code),
        )
        object.__setattr__(
            self,
            "family",
            normalize_required_text("family", self.family),
        )
        object.__setattr__(
            self,
            "manufacturer",
            normalize_required_text(
                "manufacturer",
                self.manufacturer,
            ),
        )
        object.__setattr__(
            self,
            "device_type",
            normalize_required_text(
                "device_type",
                self.device_type,
            ),
        )

        for field_name in (
            "trip_unit",
            "role",
            "notes",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(
                    field_name,
                    getattr(self, field_name),
                ),
            )

        require_positive_decimal(
            "rated_current_a",
            self.rated_current_a,
        )
        require_positive_decimal(
            "breaking_capacity_ka",
            self.breaking_capacity_ka,
        )
@dataclass(frozen=True, slots=True)
class CoordinationCatalogueEntry:
    """One coordination catalogue record."""

    code: str
    objective: CoordinationObjective
    verification_status: CoordinationVerificationStatus

    upstream_device: CoordinationDeviceReference
    downstream_device: CoordinationDeviceReference

    maximum_selective_current_ka: Decimal | None = None
    maximum_cascading_fault_level_ka: Decimal | None = None

    starter_method: StarterMethod | None = None
    motor_power_kw: Decimal | None = None

    manufacturer_document: str | None = None
    document_revision: str | None = None
    cpwd_reference: str | None = None
    standard_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "code",
            normalize_required_text("code", self.code),
        )

        for field_name in (
            "manufacturer_document",
            "document_revision",
            "cpwd_reference",
            "standard_reference",
            "notes",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(
                    field_name,
                    getattr(self, field_name),
                ),
            )

        if not isinstance(
            self.objective,
            CoordinationObjective,
        ):
            raise TypeError(
                "objective must be a CoordinationObjective value"
            )

        if not isinstance(
            self.verification_status,
            CoordinationVerificationStatus,
        ):
            raise TypeError(
                "verification_status must be a "
                "CoordinationVerificationStatus value"
            )

        if not isinstance(
            self.upstream_device,
            CoordinationDeviceReference,
        ):
            raise TypeError(
                "upstream_device must be a "
                "CoordinationDeviceReference record"
            )

        if not isinstance(
            self.downstream_device,
            CoordinationDeviceReference,
        ):
            raise TypeError(
                "downstream_device must be a "
                "CoordinationDeviceReference record"
            )

        for field_name, value in {
            "maximum_selective_current_ka": (
                self.maximum_selective_current_ka
            ),
            "maximum_cascading_fault_level_ka": (
                self.maximum_cascading_fault_level_ka
            ),
            "motor_power_kw": self.motor_power_kw,
        }.items():
            if value is not None:
                require_positive_decimal(field_name, value)

        if (
            self.starter_method is not None
            and not isinstance(
                self.starter_method,
                StarterMethod,
            )
        ):
            raise TypeError(
                "starter_method must be a StarterMethod value or None"
            )

        if (
            self.objective is CoordinationObjective.SELECTIVITY
            and self.maximum_selective_current_ka is None
        ):
            raise ValueError(
                "SELECTIVITY requires "
                "maximum_selective_current_ka"
            )

        if (
            self.objective is CoordinationObjective.CASCADING
            and self.maximum_cascading_fault_level_ka is None
        ):
            raise ValueError(
                "CASCADING requires "
                "maximum_cascading_fault_level_ka"
            )

        if self.objective in {
            CoordinationObjective.TYPE_1,
            CoordinationObjective.TYPE_2,
        }:
            if self.starter_method is None:
                raise ValueError(
                    "TYPE_1 and TYPE_2 require starter_method"
                )

            if self.motor_power_kw is None:
                raise ValueError(
                    "TYPE_1 and TYPE_2 require motor_power_kw"
                )

        if (
            self.verification_status
            is CoordinationVerificationStatus.VERIFIED
            and self.manufacturer_document is None
        ):
            raise ValueError(
                "VERIFIED coordination requires "
                "manufacturer_document"
            )

@dataclass(frozen=True, slots=True)
class CoordinationStudyInput:
    """Immutable protection-coordination study input."""

    code: str
    name: str

    objective: CoordinationObjective
    prospective_fault_current_ka: Decimal

    upstream_device: CoordinationDeviceReference
    downstream_device: CoordinationDeviceReference

    catalogue_entries: tuple[
        CoordinationCatalogueEntry,
        ...,
    ]

    required_motor_power_kw: Decimal | None = None
    required_starter_method: StarterMethod | None = None

    require_verified_entry: bool = True

    cpwd_reference: str | None = None
    standard_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the coordination study input."""

        object.__setattr__(
            self,
            "code",
            normalize_required_text(
                "code",
                self.code,
            ),
        )
        object.__setattr__(
            self,
            "name",
            normalize_required_text(
                "name",
                self.name,
            ),
        )

        for field_name in (
            "cpwd_reference",
            "standard_reference",
            "notes",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(
                    field_name,
                    getattr(self, field_name),
                ),
            )

        if not isinstance(
            self.objective,
            CoordinationObjective,
        ):
            raise TypeError(
                "objective must be a CoordinationObjective value"
            )

        require_positive_decimal(
            "prospective_fault_current_ka",
            self.prospective_fault_current_ka,
        )

        if not isinstance(
            self.upstream_device,
            CoordinationDeviceReference,
        ):
            raise TypeError(
                "upstream_device must be a "
                "CoordinationDeviceReference record"
            )

        if not isinstance(
            self.downstream_device,
            CoordinationDeviceReference,
        ):
            raise TypeError(
                "downstream_device must be a "
                "CoordinationDeviceReference record"
            )

        if not isinstance(
            self.catalogue_entries,
            tuple,
        ):
            raise TypeError(
                "catalogue_entries must be a tuple"
            )

        if not self.catalogue_entries:
            raise ValueError(
                "at least one coordination catalogue entry "
                "is required"
            )

        if not all(
            isinstance(
                entry,
                CoordinationCatalogueEntry,
            )
            for entry in self.catalogue_entries
        ):
            raise TypeError(
                "catalogue_entries must contain only "
                "CoordinationCatalogueEntry records"
            )

        entry_codes = tuple(
            entry.code
            for entry in self.catalogue_entries
        )

        if len(entry_codes) != len(set(entry_codes)):
            raise ValueError(
                "coordination catalogue entry codes "
                "must be unique"
            )

        if self.required_motor_power_kw is not None:
            require_positive_decimal(
                "required_motor_power_kw",
                self.required_motor_power_kw,
            )

        if (
            self.required_starter_method is not None
            and not isinstance(
                self.required_starter_method,
                StarterMethod,
            )
        ):
            raise TypeError(
                "required_starter_method must be a "
                "StarterMethod value or None"
            )

        if self.objective in {
            CoordinationObjective.TYPE_1,
            CoordinationObjective.TYPE_2,
        }:
            if self.required_motor_power_kw is None:
                raise ValueError(
                    "TYPE_1 and TYPE_2 studies require "
                    "required_motor_power_kw"
                )

            if self.required_starter_method is None:
                raise ValueError(
                    "TYPE_1 and TYPE_2 studies require "
                    "required_starter_method"
                )

        if not isinstance(
            self.require_verified_entry,
            bool,
        ):
            raise TypeError(
                "require_verified_entry must be a boolean"
            )


__all__ = [
    "CoordinationCatalogueEntry",
    "CoordinationDeviceReference",
    "CoordinationObjective",
    "CoordinationStudyInput",
    "CoordinationVerificationStatus",
    "StarterMethod",
]
