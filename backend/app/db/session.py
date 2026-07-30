"""
Database session dependency.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import AsyncSessionFactory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an AsyncSession for dependency injection.
    """

    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()