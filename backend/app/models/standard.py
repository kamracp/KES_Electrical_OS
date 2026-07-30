"""
Engineering Standards Model.
KESE-S1-M3
"""

from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Integer,
    String,
    Text,
)
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
    Master registry of electrical engineering standards.

    Stores standards issued by organizations such as IEC, IEEE,
    BIS, NFPA, NEMA, ISO, ANSI, and other recognized authorities.
    """

    __tablename__ = "standards"

    __table_args__ = (
        CheckConstraint(
            (
                "publication_year IS NULL "
                "OR publication_year BETWEEN 1800 AND 2100"
            ),
            name="publication_year_range",
        ),
        CheckConstraint(
            (
                "withdrawn_date IS NULL "
                "OR effective_date IS NULL "
                "OR withdrawn_date >= effective_date"
            ),
            name="valid_lifecycle_dates",
        ),
    )

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    issuing_organization: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    edition: Mapped[str | None] = mapped_column(
        String(100),
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
        index=True,
    )

    effective_date: Mapped[date | None] = mapped_column(
        Date,
    )

    withdrawn_date: Mapped[date | None] = mapped_column(
        Date,
    )

    scope: Mapped[str | None] = mapped_column(
        Text,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
    )

    reference_url: Mapped[str | None] = mapped_column(
        String(500),
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
            f"issuing_organization='{self.issuing_organization}', "
            f"status='{self.status}')>"
        )
