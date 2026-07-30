"""
Pydantic schemas for Engineering Units.
KESE-S1-M4
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


def reject_float_conversion_factor(value: object) -> object:
    """
    Reject binary floating-point input.

    Exact conversion factors must be supplied as a decimal string,
    integer, or Decimal value.
    """

    if isinstance(value, float):
        raise ValueError(
            "conversion_factor must be provided as a decimal string, "
            "integer, or Decimal"
        )

    return value


class UnitBase(BaseModel):
    """Shared Engineering Unit fields."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    code: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )

    quantity: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    unit_system: str = Field(
        default="SI",
        min_length=1,
        max_length=30,
    )

    si_unit: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )

    conversion_factor: Decimal = Field(
        default=Decimal("1"),
        gt=Decimal("0"),
        max_digits=38,
        decimal_places=18,
        examples=["0.001"],
    )

    is_base_unit: bool = False
    description: str | None = None
    remarks: str | None = None
    is_active: bool = True

    @field_validator(
        "conversion_factor",
        mode="before",
    )
    @classmethod
    def validate_conversion_factor_input(
        cls,
        value: object,
    ) -> object:
        """Prevent conversion through binary floating-point input."""

        return reject_float_conversion_factor(value)


class UnitCreate(UnitBase):
    """Schema for creating an Engineering Unit."""


class UnitUpdate(BaseModel):
    """Schema for partially updating an Engineering Unit."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    symbol: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    quantity: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    unit_system: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )

    si_unit: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    conversion_factor: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        max_digits=38,
        decimal_places=18,
    )

    is_base_unit: bool | None = None
    description: str | None = None
    remarks: str | None = None
    is_active: bool | None = None

    @field_validator(
        "conversion_factor",
        mode="before",
    )
    @classmethod
    def validate_conversion_factor_input(
        cls,
        value: object,
    ) -> object:
        """Prevent conversion through binary floating-point input."""

        return reject_float_conversion_factor(value)


class UnitResponse(UnitBase):
    """Schema returned by the Engineering Units API."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: UUID
    created_at: datetime
    updated_at: datetime