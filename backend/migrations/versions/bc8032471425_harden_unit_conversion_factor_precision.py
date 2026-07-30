"""Harden unit conversion factor precision.

Revision ID: bc8032471425
Revises: c4f1a2b3d4e5
Create Date: 2026-07-26 15:33:33.579299
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "bc8032471425"
down_revision: Union[str, Sequence[str], None] = "c4f1a2b3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store unit conversion factors as exact positive decimals."""

    op.alter_column(
        "units",
        "conversion_factor",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        type_=sa.Numeric(
            precision=38,
            scale=18,
        ),
        existing_nullable=False,
        postgresql_using=(
            "conversion_factor::numeric(38, 18)"
        ),
    )

    op.create_check_constraint(
        op.f("ck_units_conversion_factor_positive"),
        "units",
        "conversion_factor > 0",
    )


def downgrade() -> None:
    """Restore floating-point unit conversion factors."""

    op.drop_constraint(
        op.f("ck_units_conversion_factor_positive"),
        "units",
        type_="check",
    )

    op.alter_column(
        "units",
        "conversion_factor",
        existing_type=sa.Numeric(
            precision=38,
            scale=18,
        ),
        type_=sa.DOUBLE_PRECISION(precision=53),
        existing_nullable=False,
        postgresql_using=(
            "conversion_factor::double precision"
        ),
    )