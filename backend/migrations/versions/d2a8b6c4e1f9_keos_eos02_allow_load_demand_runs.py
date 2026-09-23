"""keos eos02 allow load demand runs

Revision ID: d2a8b6c4e1f9
Revises: c9f5a3b7d2e4
Create Date: 2026-09-23 00:00:00.000000

Widen the calculation_type CHECK of calculation_runs so the load and demand
engine may persist its runs in the generic table (Master Prompt A15 (d)).

Written by hand: Alembic autogenerate does not detect CHECK constraint
changes, so this migration is not reproducible with --autogenerate.

The downgrade restores the two-value CHECK and therefore fails while any
LOAD_DEMAND row exists. That is intended: a run is engineering evidence and
is never silently deleted to make a downgrade succeed.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd2a8b6c4e1f9'
down_revision: Union[str, Sequence[str], None] = 'c9f5a3b7d2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Alembic applies the metadata naming convention (app/db/base.py) to this name on both
# drop and create, so the short name is given here and PostgreSQL sees
# ck_calculation_runs_type_valid. Passing the full name would prefix it a second time.
CONSTRAINT_NAME = "type_valid"
TABLE_NAME = "calculation_runs"

TYPES_BEFORE = ("CABLE_SIZING", "SHORT_CIRCUIT")
TYPES_AFTER = ("CABLE_SIZING", "SHORT_CIRCUIT", "LOAD_DEMAND")


def _condition(types: Sequence[str]) -> str:
    """Build the CHECK condition for the given calculation types."""

    quoted = ", ".join(f"'{value}'" for value in types)

    return f"calculation_type IN ({quoted})"


def upgrade() -> None:
    """Allow LOAD_DEMAND runs in calculation_runs (EOS-02)."""

    op.drop_constraint(CONSTRAINT_NAME, TABLE_NAME, type_="check")
    op.create_check_constraint(
        CONSTRAINT_NAME,
        TABLE_NAME,
        _condition(TYPES_AFTER),
    )


def downgrade() -> None:
    """Restore the cable and fault only CHECK; fails if LOAD_DEMAND rows exist."""

    op.drop_constraint(CONSTRAINT_NAME, TABLE_NAME, type_="check")
    op.create_check_constraint(
        CONSTRAINT_NAME,
        TABLE_NAME,
        _condition(TYPES_BEFORE),
    )
