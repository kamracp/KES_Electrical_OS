"""Upgrade standards table for KESE-S1-M3.

Revision ID: c4f1a2b3d4e5
Revises: 90c8a737dfe4
Create Date: 2026-07-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision: str = "c4f1a2b3d4e5"
down_revision: Union[str, Sequence[str], None] = "90c8a737dfe4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade the standards registry for KESE-S1-M3."""

    op.drop_index(
        op.f("ix_standards_organization"),
        table_name="standards",
    )

    op.alter_column(
        "standards",
        "organization",
        new_column_name="issuing_organization",
        existing_type=sa.String(length=50),
        type_=sa.String(length=100),
        existing_nullable=False,
    )

    op.alter_column(
        "standards",
        "code",
        existing_type=sa.String(length=50),
        type_=sa.String(length=100),
        existing_nullable=False,
    )

    op.alter_column(
        "standards",
        "edition",
        existing_type=sa.String(length=50),
        type_=sa.String(length=100),
        existing_nullable=True,
    )

    op.add_column(
        "standards",
        sa.Column(
            "scope",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "standards",
        sa.Column(
            "reference_url",
            sa.String(length=500),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_standards_issuing_organization"),
        "standards",
        ["issuing_organization"],
        unique=False,
    )

    op.create_index(
        op.f("ix_standards_status"),
        "standards",
        ["status"],
        unique=False,
    )

    op.create_check_constraint(
        op.f("ck_standards_publication_year_range"),
        "standards",
        (
            "publication_year IS NULL "
            "OR publication_year BETWEEN 1800 AND 2100"
        ),
    )

    op.create_check_constraint(
        op.f("ck_standards_valid_lifecycle_dates"),
        "standards",
        (
            "withdrawn_date IS NULL "
            "OR effective_date IS NULL "
            "OR withdrawn_date >= effective_date"
        ),
    )


def downgrade() -> None:
    """Restore the previous standards table structure."""

    op.drop_constraint(
        op.f("ck_standards_valid_lifecycle_dates"),
        "standards",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_standards_publication_year_range"),
        "standards",
        type_="check",
    )

    op.drop_index(
        op.f("ix_standards_status"),
        table_name="standards",
    )

    op.drop_index(
        op.f("ix_standards_issuing_organization"),
        table_name="standards",
    )

    op.drop_column(
        "standards",
        "reference_url",
    )

    op.drop_column(
        "standards",
        "scope",
    )

    op.alter_column(
        "standards",
        "edition",
        existing_type=sa.String(length=100),
        type_=sa.String(length=50),
        existing_nullable=True,
    )

    op.alter_column(
        "standards",
        "code",
        existing_type=sa.String(length=100),
        type_=sa.String(length=50),
        existing_nullable=False,
    )

    op.alter_column(
        "standards",
        "issuing_organization",
        new_column_name="organization",
        existing_type=sa.String(length=100),
        type_=sa.String(length=50),
        existing_nullable=False,
    )

    op.create_index(
        op.f("ix_standards_organization"),
        "standards",
        ["organization"],
        unique=False,
    )
