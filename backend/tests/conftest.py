"""
Shared pytest fixtures for KES Electrical OS backend tests.
"""

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.models.calculation_run
import app.models.identity
import app.models.load_calculation_run
import app.models.standard
import app.models.unit
from app.api.authentication import require_user
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models.identity import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    User,
    UserSession,
)
from app.services.auth import AuthenticatedSession

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Create an isolated in-memory database for each test."""

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

        await engine.dispose()


@pytest_asyncio.fixture
async def anonymous_client(
    test_engine: AsyncEngine,
) -> AsyncIterator[AsyncClient]:
    """An API client with an isolated database and no signed-in user."""

    test_session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with test_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def make_identity() -> Callable[[OrganizationRole], AuthenticatedSession]:
    """Build a signed-in identity with the given role, without touching the database."""

    def build(role: OrganizationRole) -> AuthenticatedSession:
        now = datetime.now(UTC)
        organization = Organization(id=uuid4(), code="TEST", name="Test Organization")
        user = User(
            id=uuid4(),
            email=f"{role.value.lower()}@example.com",
            full_name=f"Test {role.value.title()}",
            is_active=True,
            must_change_password=False,
        )
        membership = OrganizationMembership(
            id=uuid4(),
            organization_id=organization.id,
            user_id=user.id,
            role=role.value,
            is_active=True,
        )
        session = UserSession(
            id=uuid4(),
            user_id=user.id,
            organization_id=organization.id,
            token_hash="0" * 64,
            expires_at=now + timedelta(days=7),
            last_seen_at=now,
        )
        return AuthenticatedSession(user, organization, membership, session)

    return build


@pytest.fixture
def sign_in_as(
    anonymous_client: AsyncClient,
    make_identity: Callable[[OrganizationRole], AuthenticatedSession],
) -> Callable[[OrganizationRole], AsyncClient]:
    """Make the shared client act as a signed-in member with the given role."""

    def sign_in(role: OrganizationRole) -> AsyncClient:
        identity = make_identity(role)
        app.dependency_overrides[require_user] = lambda: identity
        return anonymous_client

    return sign_in


@pytest.fixture
def client(sign_in_as: Callable[[OrganizationRole], AsyncClient]) -> AsyncClient:
    """The default API client: signed in as an owner, so module tests need no sign-in step."""

    return sign_in_as(OrganizationRole.OWNER)


@pytest.fixture
def standard_payload() -> dict[str, object]:
    """Return a valid Engineering Standard request payload."""

    return {
        "code": "IEC 60364-1:2025",
        "title": ("Low-voltage electrical installations — Fundamental principles"),
        "issuing_organization": "IEC",
        "category": "Electrical Installations",
        "edition": "2025 Edition",
        "publication_year": 2025,
        "country": "International",
        "status": "ACTIVE",
        "effective_date": "2025-01-01",
        "withdrawn_date": None,
        "scope": (
            "Fundamental principles and requirements for low-voltage electrical installations."
        ),
        "description": (
            "Engineering standard used for electrical installation design and compliance."
        ),
        "reference_url": "https://www.iec.ch",
        "remarks": "KESE-S1-M3 automated test record.",
        "is_active": True,
    }
