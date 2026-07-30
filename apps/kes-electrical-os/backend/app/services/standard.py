"""
Service layer for Engineering Standards.
KESE-S1-M3
"""

from uuid import UUID

from app.models.standard import Standard
from app.repositories.standard import StandardRepository
from app.schemas.standard import StandardCreate, StandardUpdate


class StandardService:
    """Business logic for Engineering Standards."""

    def __init__(self, repository: StandardRepository):
        self.repository = repository

    async def create(
        self,
        payload: StandardCreate,
    ) -> Standard:
        """Create and persist a new Engineering Standard."""

        standard = Standard(**payload.model_dump())

        return await self.repository.create(standard)

    async def list(self) -> list[Standard]:
        """Return all Engineering Standards."""

        return await self.repository.list()

    async def get_by_id(
        self,
        standard_id: UUID,
    ) -> Standard | None:
        """Return an Engineering Standard by UUID."""

        return await self.repository.get_by_id(standard_id)

    async def get_by_code(
        self,
        code: str,
    ) -> Standard | None:
        """Return an Engineering Standard by unique code."""

        return await self.repository.get_by_code(code)

    async def update(
        self,
        standard: Standard,
        payload: StandardUpdate,
    ) -> Standard:
        """Apply partial updates to an Engineering Standard."""

        updates = payload.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(standard, field, value)

        return await self.repository.update(standard)

    async def delete(
        self,
        standard: Standard,
    ) -> None:
        """Delete an Engineering Standard."""

        await self.repository.delete(standard)
