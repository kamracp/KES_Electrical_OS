"""
Pydantic schemas for Engineering Units.
KESE-S1-M2
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UnitBase(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    symbol: str = Field(..., max_length=20)
    quantity: str = Field(..., max_length=100)
    unit_system: str = Field(default="SI", max_length=30)
    si_unit: str = Field(..., max_length=20)
    conversion_factor: float = 1.0
    is_base_unit: bool = False
    description: str | None = None
    remarks: str | None = None
    is_active: bool = True


class UnitCreate(UnitBase):
    """Create schema."""


class UnitUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, max_length=20)
    name: str | None = Field(default=None, max_length=100)
    symbol: str | None = Field(default=None, max_length=20)
    quantity: str | None = Field(default=None, max_length=100)
    unit_system: str | None = Field(default=None, max_length=30)
    si_unit: str | None = Field(default=None, max_length=20)
    conversion_factor: float | None = None
    is_base_unit: bool | None = None
    description: str | None = None
    remarks: str | None = None
    is_active: bool | None = None


class UnitResponse(UnitBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime