"""Persistence tests for the calculation_type CHECK of calculation_runs (EOS-02, A15 (d))."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.calculation_run import CalculationRun, EngineeringCalculationType

pytestmark = pytest.mark.persistence

TYPE_CONSTRAINT = "ck_calculation_runs_type_valid"


@pytest_asyncio.fixture
async def db(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


def run(*, calculation_type: str) -> CalculationRun:
    """Create an unassigned run of the given calculation type."""

    return CalculationRun(
        project_revision_id=None,
        module_code="EOS-02",
        calculation_type=calculation_type,
        calculation_key="LOAD-001",
        revision_number=1,
        engine_version="load-engine 0.1.0",
        design_check_status="PASS",
        jurisdiction_profile="IN",
        reference_verification_status="VERIFIED",
        input_snapshot={"code": "LOAD-001"},
        result_snapshot={"status": "VALID"},
        content_hash="b" * 64,
    )


async def test_a_load_demand_run_can_be_saved(db: AsyncSession) -> None:
    """The load engine persists into the generic table (A15 (d))."""

    db.add(run(calculation_type=EngineeringCalculationType.LOAD_DEMAND.value))
    await db.commit()

    saved = (
        await db.execute(select(CalculationRun).where(CalculationRun.calculation_key == "LOAD-001"))
    ).scalar_one()

    assert saved.calculation_type == "LOAD_DEMAND"
    assert saved.module_code == "EOS-02"


async def test_an_unknown_calculation_type_is_refused(db: AsyncSession) -> None:
    """The CHECK constraint keeps unregistered engines out of the table."""

    db.add(run(calculation_type="BOGUS"))

    with pytest.raises(IntegrityError):
        await db.commit()


def test_the_enum_and_the_check_list_the_same_types() -> None:
    """Drift guard: the CHECK text is built from the enum, so both must agree."""

    constraint = next(
        constraint
        for constraint in CalculationRun.__table__.constraints
        if constraint.name == TYPE_CONSTRAINT
    )

    condition = str(constraint.sqltext)

    assert {member.value for member in EngineeringCalculationType} == {
        "CABLE_SIZING",
        "SHORT_CIRCUIT",
        "LOAD_DEMAND",
    }

    for member in EngineeringCalculationType:
        assert f"'{member.value}'" in condition

    assert condition.count("'") == 2 * len(EngineeringCalculationType)
