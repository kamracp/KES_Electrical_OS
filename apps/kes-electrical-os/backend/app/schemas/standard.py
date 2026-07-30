"""
Pydantic schemas for Engineering Standards.
KESE-S1-M3
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class StandardBase(BaseModel):
    """Shared fields for Engineering Standard schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    code: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["IEC 60364-1"],
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=300,
        examples=[
            "Low-voltage electrical installations — "
            "Fundamental principles"
        ],
    )

    issuing_organization: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["IEC"],
    )

    category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Electrical Installations"],
    )

    edition: str | None = Field(
        default=None,
        max_length=100,
        examples=["6th Edition"],
    )

    publication_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
        examples=[2022],
    )

    country: str | None = Field(
        default=None,
        max_length=100,
        examples=["International"],
    )

    status: str = Field(
        default="ACTIVE",
        min_length=1,
        max_length=30,
        examples=["ACTIVE"],
    )

    effective_date: date | None = None
    withdrawn_date: date | None = None

    scope: str | None = None
    description: str | None = None

    reference_url: str | None = Field(
        default=None,
        max_length=500,
        examples=["https://www.iec.ch"],
    )

    remarks: str | None = None

    is_active: bool = True

    @model_validator(mode="after")
    def validate_lifecycle_dates(self) -> "StandardBase":
        if (
            self.effective_date is not None
            and self.withdrawn_date is not None
            and self.withdrawn_date < self.effective_date
        ):
            raise ValueError(
                "withdrawn_date cannot be earlier than effective_date"
            )

        return self


class StandardCreate(StandardBase):
    """Schema for creating an Engineering Standard."""


class StandardUpdate(BaseModel):
    """Schema for partially updating an Engineering Standard."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=300,
    )

    issuing_organization: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    edition: str | None = Field(
        default=None,
        max_length=100,
    )

    publication_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
    )

    country: str | None = Field(
        default=None,
        max_length=100,
    )

    status: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )

    effective_date: date | None = None
    withdrawn_date: date | None = None

    scope: str | None = None
    description: str | None = None

    reference_url: str | None = Field(
        default=None,
        max_length=500,
    )

    remarks: str | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_lifecycle_dates(self) -> "StandardUpdate":
        if (
            self.effective_date is not None
            and self.withdrawn_date is not None
            and self.withdrawn_date < self.effective_date
        ):
            raise ValueError(
                "withdrawn_date cannot be earlier than effective_date"
            )

        return self


class StandardResponse(StandardBase):
    """Schema returned by the Engineering Standards API."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: UUID
    created_at: datetime
    updated_at: datetime
