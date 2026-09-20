"""
Guard against a model without a migration.

The API tests build their database straight from the ORM models, so a table that has a model
but no Alembic migration would pass every test and be missing on the live database. This test
reads the migration files and checks that each model table is created by one of them.
"""

import re
from pathlib import Path

import pytest

import app.models.calculation_run
import app.models.identity
import app.models.load_calculation_run
import app.models.standard
import app.models.unit  # noqa: F401
from app.db.base import Base

pytestmark = pytest.mark.persistence

VERSIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"


def test_every_model_table_is_created_by_a_migration() -> None:
    created: set[str] = set()
    for migration in VERSIONS.glob("*.py"):
        source = migration.read_text(encoding="utf-8")
        created.update(re.findall(r"create_table\(\s*['\"]([a-z_]+)['\"]", source))

    missing = sorted(set(Base.metadata.tables) - created)

    assert missing == [], f"model tables without a migration: {missing}"
