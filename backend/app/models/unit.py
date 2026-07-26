"""
Engineering Units Model.
KESE-S1-M2
"""

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Unit(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """
    Engineering Units master library.
    """

    __tablename__ = "units"

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    quantity: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    unit_system: Mapped[str] = mapped_column(
        String(30),
        default="SI",
        nullable=False,
        index=True,
    )

    si_unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    conversion_factor: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )

    is_base_unit: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Unit(code='{self.code}', "
            f"quantity='{self.quantity}')>"
        )