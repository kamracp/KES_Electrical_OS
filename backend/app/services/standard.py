"""
Service layer for Standards Registry.
KEOS-S1-M1
"""

from uuid import UUID

from app.models.standard import Standard
from app.repositories.standard import StandardRepository
from app.schemas.standard import (
    StandardCreate,
    StandardUpdate,
)


class StandardService:
    """Business logic for Standards Registry."""

    def __init__(self, repository: StandardRepository):
        self._repository = repository

    async def create(self, payload: StandardCreate) -> Standard:
        standard = Standard(**payload.model_dump())
        return await self._repository.create(standard)

    async def get(self, standard_id: UUID) -> Standard | None:
        return await self._repository.get(standard_id)

    async def get_by_code(self, code: str) -> Standard | None:
        return await self._repository.get_by_code(code)

    async def list(self) -> list[Standard]:
        return await self._repository.list()

    async def update(
        self,
        standard: Standard,
        payload: StandardUpdate,
    ) -> Standard:
        for key, value in payload.model_dump(
            exclude_unset=True
        ).items():
            setattr(standard, key, value)

        return await self._repository.update(standard)

    async def delete(self, standard: Standard) -> None:
        await self._repository.delete(standard)