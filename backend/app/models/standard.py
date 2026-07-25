"""
Standards Registry Model
KEOS-S1-M1
"""

from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Standard(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """
    Master engineering standards registry.
    """

    __tablename__ = "standards"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    organization: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    edition: Mapped[str | None] = mapped_column(
        String(50),
    )

    publication_year: Mapped[int | None] = mapped_column(
        Integer,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE",
        nullable=False,
    )

    effective_date: Mapped[date | None] = mapped_column(
        Date,
    )

    withdrawn_date: Mapped[date | None] = mapped_column(
        Date,
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
            f"<Standard(code='{self.code}', "
            f"organization='{self.organization}')>"
        )