"""
Shared API dependencies.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.standard import StandardRepository
from app.services.standard import StandardService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Shared database session dependency.
    """
    async for session in get_db_session():
        yield session


def get_standard_repository(
    session: AsyncSession,
) -> StandardRepository:
    """
    Construct the Standards repository.
    """
    return StandardRepository(session)


def get_standard_service(
    repository: StandardRepository,
) -> StandardService:
    """
    Construct the Standards service.
    """
    return StandardService(repository)