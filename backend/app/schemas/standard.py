"""
Pydantic schemas for the Standards Registry.
KEOS-S1-M1
"""

from datetime import date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StandardBase(BaseModel):
    """Shared fields for Standards."""

    code: str = Field(max_length=50)
    title: str = Field(max_length=300)
    organization: str = Field(max_length=50)
    category: str = Field(max_length=100)

    edition: str | None = Field(default=None, max_length=50)
    publication_year: int | None = None
    country: str | None = Field(default=None, max_length=100)

    status: str = "ACTIVE"

    effective_date: date | None = None
    withdrawn_date: date | None = None

    description: str | None = None
    remarks: str | None = None

    is_active: bool = True


class StandardCreate(StandardBase):
    """Schema for creating a Standard."""


class StandardUpdate(BaseModel):
    """Schema for updating a Standard."""

    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=300)
    organization: str | None = Field(default=None, max_length=50)
    category: str | None = Field(default=None, max_length=100)

    edition: str | None = Field(default=None, max_length=50)
    publication_year: int | None = None
    country: str | None = Field(default=None, max_length=100)

    status: str | None = None

    effective_date: date | None = None
    withdrawn_date: date | None = None

    description: str | None = None
    remarks: str | None = None

    is_active: bool | None = None


class StandardResponse(StandardBase):
    """Schema returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime