"""
Repository for the project spine (EOS-01 b): sites, projects and project revisions.

Every lookup is scoped by organization so that one organization never sees another's sites
or projects. Like IdentityRepository, the write methods only stage changes and the service
ends each operation with one commit(): a project and its first revision reach the database
together or not at all. Nothing is deleted; sites are deactivated and projects archived.
"""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectRevision, ProjectRevisionStatus, Site


class ProjectRepository:
    """Persistence and retrieval for sites, projects and project revisions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # -- unit of work ---------------------------------------------------------------------

    def add(self, *entities: object) -> None:
        """Stage new records; nothing is written before commit()."""

        self.db.add_all(entities)

    async def flush(self) -> None:
        """Send staged changes so that generated ids are available; still not committed."""

        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()

    async def refresh(self, entity: object) -> None:
        await self.db.refresh(entity)

    # -- sites ----------------------------------------------------------------------------

    async def get_site(self, site_id: UUID) -> Site | None:
        return await self.db.get(Site, site_id)

    async def get_site_by_code(self, organization_id: UUID, code: str) -> Site | None:
        stmt = select(Site).where(Site.organization_id == organization_id, Site.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_sites(
        self, organization_id: UUID, *, include_inactive: bool = False
    ) -> list[Site]:
        stmt = select(Site).where(Site.organization_id == organization_id)
        if not include_inactive:
            stmt = stmt.where(Site.is_active.is_(True))
        stmt = stmt.order_by(Site.code)
        return list((await self.db.execute(stmt)).scalars().all())

    # -- projects -------------------------------------------------------------------------

    async def get_project(self, project_id: UUID) -> Project | None:
        return await self.db.get(Project, project_id)

    async def get_project_by_code(self, organization_id: UUID, code: str) -> Project | None:
        stmt = select(Project).where(
            Project.organization_id == organization_id, Project.code == code
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_projects(
        self, organization_id: UUID, *, status: str | None = None
    ) -> list[Project]:
        stmt = select(Project).where(Project.organization_id == organization_id)
        if status is not None:
            stmt = stmt.where(Project.status == status)
        stmt = stmt.order_by(Project.code)
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_projects_of_site(self, site_id: UUID) -> int:
        stmt = select(func.count()).select_from(Project).where(Project.site_id == site_id)
        return int((await self.db.execute(stmt)).scalar_one())

    # -- revisions ------------------------------------------------------------------------

    async def get_revision(self, revision_id: UUID) -> ProjectRevision | None:
        return await self.db.get(ProjectRevision, revision_id)

    async def list_revisions(self, project_id: UUID) -> list[ProjectRevision]:
        """All revisions of a project, newest first."""

        stmt = (
            select(ProjectRevision)
            .where(ProjectRevision.project_id == project_id)
            .order_by(ProjectRevision.revision_number.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_open_revision(self, project_id: UUID) -> ProjectRevision | None:
        """The one revision of a project that still accepts runs, if any."""

        stmt = (
            select(ProjectRevision)
            .where(
                ProjectRevision.project_id == project_id,
                ProjectRevision.status == ProjectRevisionStatus.OPEN.value,
            )
            .order_by(ProjectRevision.revision_number.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_next_revision_number(self, project_id: UUID) -> int:
        stmt = select(func.coalesce(func.max(ProjectRevision.revision_number), 0) + 1).where(
            ProjectRevision.project_id == project_id
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def list_revisions_with_projects(
        self, organization_id: UUID, revision_ids: Collection[UUID]
    ) -> list[tuple[ProjectRevision, Project]]:
        """The named revisions of this organization with their projects, in one query.

        A list of runs names many revisions; this answers all of them at once instead of one
        query per run. Revisions of another organization are simply not returned.
        """

        if not revision_ids:
            return []
        stmt = (
            select(ProjectRevision, Project)
            .join(Project, Project.id == ProjectRevision.project_id)
            .where(
                ProjectRevision.id.in_(set(revision_ids)),
                Project.organization_id == organization_id,
            )
        )
        return [(revision, project) for revision, project in (await self.db.execute(stmt)).all()]


__all__ = ["ProjectRepository"]
