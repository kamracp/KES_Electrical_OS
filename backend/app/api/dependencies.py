"""
Shared API dependencies.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.standard import StandardRepository
from app.services.standard import StandardService

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a shared database session dependency."""

    async for session in get_db_session():
        yield session


def get_standard_repository(
    session: AsyncSession,
) -> StandardRepository:
    """Construct the Standards repository."""

    return StandardRepository(session)


def get_standard_service(
    repository: StandardRepository,
) -> StandardService:
    """Construct the Standards service."""

    return StandardService(repository)


__all__ = [
    "DatabaseSession",
    "get_session",
    "get_standard_repository",
    "get_standard_service",
]