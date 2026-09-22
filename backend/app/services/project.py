"""
Project spine service (EOS-01 b): sites, projects and project revisions of one organization.

Rules that the database cannot express alone live here: a project's site belongs to the
project's organization; creating a project also creates its revision 1 in one commit; a
project has at most one OPEN revision - a new revision supersedes the open one, and an
issued revision is never reopened; archived projects accept no new revisions or runs.
Roles are enforced by the API layer (app.api.router), not here.
"""

from collections.abc import Callable, Collection
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.domain.electrical.jurisdiction import JurisdictionProfile
from app.models.project import (
    Project,
    ProjectRevision,
    ProjectRevisionStatus,
    ProjectStatus,
    Site,
)
from app.repositories.project import ProjectRepository

FIRST_REVISION_LABEL = "Rev 1"


class ProjectError(Exception):
    """Base class; the message is safe to show to the user."""


class ProjectNotFoundError(ProjectError):
    """No such site, project or revision in the caller's organization."""


class ProjectConflictError(ProjectError):
    """The change contradicts the current state or a rule."""


class ProjectService:
    """Sites, projects and revisions of the caller's organization."""

    def __init__(
        self,
        repository: ProjectRepository,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self._now = now or (lambda: datetime.now(UTC))

    # -- sites ----------------------------------------------------------------------------

    async def list_sites(
        self, organization_id: UUID, *, include_inactive: bool = False
    ) -> list[Site]:
        return await self.repository.list_sites(organization_id, include_inactive=include_inactive)

    async def get_site(self, organization_id: UUID, site_id: UUID) -> Site:
        site = await self.repository.get_site(site_id)
        if site is None or site.organization_id != organization_id:
            raise ProjectNotFoundError("Site not found.")
        return site

    async def create_site(
        self,
        organization_id: UUID,
        *,
        code: str,
        name: str,
        location: str | None = None,
    ) -> Site:
        code = code.strip()
        name = name.strip()
        if not code or not name:
            raise ProjectConflictError("Site code and name are required.")
        if await self.repository.get_site_by_code(organization_id, code) is not None:
            raise ProjectConflictError("A site with this code already exists.")
        site = Site(
            organization_id=organization_id,
            code=code,
            name=name,
            location=(location.strip() or None) if location else None,
        )
        self.repository.add(site)
        await self._commit_or_conflict("A site with this code already exists.")
        await self.repository.refresh(site)
        return site

    async def update_site(
        self,
        organization_id: UUID,
        site_id: UUID,
        *,
        name: str | None = None,
        location: str | None = None,
        is_active: bool | None = None,
    ) -> Site:
        site = await self.get_site(organization_id, site_id)
        if name is not None:
            if not name.strip():
                raise ProjectConflictError("Site name is required.")
            site.name = name.strip()
        if location is not None:
            site.location = location.strip() or None
        if is_active is not None:
            site.is_active = is_active
        await self.repository.commit()
        await self.repository.refresh(site)
        return site

    # -- projects -------------------------------------------------------------------------

    async def list_projects(
        self, organization_id: UUID, *, status: ProjectStatus | None = None
    ) -> list[Project]:
        return await self.repository.list_projects(
            organization_id, status=status.value if status else None
        )

    async def get_project(self, organization_id: UUID, project_id: UUID) -> Project:
        project = await self.repository.get_project(project_id)
        if project is None or project.organization_id != organization_id:
            raise ProjectNotFoundError("Project not found.")
        return project

    async def create_project(
        self,
        organization_id: UUID,
        *,
        site_id: UUID,
        code: str,
        name: str,
        jurisdiction_profile: JurisdictionProfile,
        client_name: str | None = None,
        description: str | None = None,
        created_by: str | None = None,
        first_revision_label: str = FIRST_REVISION_LABEL,
    ) -> tuple[Project, ProjectRevision]:
        """Create a project and its revision 1 (OPEN) in one commit."""

        code = code.strip()
        name = name.strip()
        if not code or not name:
            raise ProjectConflictError("Project code and name are required.")
        site = await self.get_site(organization_id, site_id)
        if not site.is_active:
            raise ProjectConflictError("The site is inactive.")
        if await self.repository.get_project_by_code(organization_id, code) is not None:
            raise ProjectConflictError("A project with this code already exists.")
        project = Project(
            organization_id=organization_id,
            site_id=site.id,
            code=code,
            name=name,
            jurisdiction_profile=jurisdiction_profile.value,
            client_name=(client_name.strip() or None) if client_name else None,
            description=(description.strip() or None) if description else None,
        )
        self.repository.add(project)
        await self.repository.flush()
        revision = ProjectRevision(
            project_id=project.id,
            revision_number=1,
            label=first_revision_label.strip() or FIRST_REVISION_LABEL,
            created_by=created_by,
        )
        self.repository.add(revision)
        await self._commit_or_conflict("A project with this code already exists.")
        await self.repository.refresh(project)
        await self.repository.refresh(revision)
        return project, revision

    async def update_project(
        self,
        organization_id: UUID,
        project_id: UUID,
        *,
        name: str | None = None,
        client_name: str | None = None,
        description: str | None = None,
    ) -> Project:
        project = await self.get_project(organization_id, project_id)
        if project.status == ProjectStatus.ARCHIVED.value:
            raise ProjectConflictError("An archived project cannot be changed.")
        if name is not None:
            if not name.strip():
                raise ProjectConflictError("Project name is required.")
            project.name = name.strip()
        if client_name is not None:
            project.client_name = client_name.strip() or None
        if description is not None:
            project.description = description.strip() or None
        await self.repository.commit()
        await self.repository.refresh(project)
        return project

    async def archive_project(self, organization_id: UUID, project_id: UUID) -> Project:
        project = await self.get_project(organization_id, project_id)
        if project.status == ProjectStatus.ARCHIVED.value:
            raise ProjectConflictError("The project is already archived.")
        project.status = ProjectStatus.ARCHIVED.value
        await self.repository.commit()
        await self.repository.refresh(project)
        return project

    # -- revisions ------------------------------------------------------------------------

    async def list_revisions(
        self, organization_id: UUID, project_id: UUID
    ) -> list[ProjectRevision]:
        project = await self.get_project(organization_id, project_id)
        return await self.repository.list_revisions(project.id)

    async def get_revision(self, organization_id: UUID, revision_id: UUID) -> ProjectRevision:
        revision = await self.repository.get_revision(revision_id)
        if revision is None:
            raise ProjectNotFoundError("Revision not found.")
        await self.get_project(organization_id, revision.project_id)
        return revision

    async def create_revision(
        self,
        organization_id: UUID,
        project_id: UUID,
        *,
        label: str,
        created_by: str | None = None,
        notes: str | None = None,
    ) -> ProjectRevision:
        """Open the next revision; the currently open one, if any, becomes SUPERSEDED."""

        project = await self.get_project(organization_id, project_id)
        if project.status == ProjectStatus.ARCHIVED.value:
            raise ProjectConflictError("An archived project cannot take a new revision.")
        label = label.strip()
        if not label:
            raise ProjectConflictError("Revision label is required.")
        current = await self.repository.get_open_revision(project.id)
        if current is not None:
            current.status = ProjectRevisionStatus.SUPERSEDED.value
        revision = ProjectRevision(
            project_id=project.id,
            revision_number=await self.repository.get_next_revision_number(project.id),
            label=label,
            created_by=created_by,
            notes=(notes.strip() or None) if notes else None,
        )
        self.repository.add(revision)
        await self._commit_or_conflict("The revision number is already taken; retry.")
        await self.repository.refresh(revision)
        return revision

    async def issue_revision(
        self,
        organization_id: UUID,
        revision_id: UUID,
        *,
        issued_by: str,
    ) -> ProjectRevision:
        """Freeze the open revision as the issued record; a new revision continues the work."""

        revision = await self.get_revision(organization_id, revision_id)
        if revision.status != ProjectRevisionStatus.OPEN.value:
            raise ProjectConflictError("Only an open revision can be issued.")
        revision.status = ProjectRevisionStatus.ISSUED.value
        revision.issued_by = issued_by
        revision.issued_at = self._now()
        await self.repository.commit()
        await self.repository.refresh(revision)
        return revision

    async def revision_summaries(
        self, organization_id: UUID, revision_ids: Collection[UUID]
    ) -> dict[UUID, tuple[Project, ProjectRevision]]:
        """Name the project and the revision behind each revision id, in one query.

        Only revisions of the caller's own organization are named, so a record that points at
        another organization's revision is answered without its project.
        """

        found = await self.repository.list_revisions_with_projects(organization_id, revision_ids)
        return {revision.id: (project, revision) for revision, project in found}

    async def revision_for_new_run(
        self, organization_id: UUID, revision_id: UUID
    ) -> tuple[Project, ProjectRevision]:
        """The revision a new calculation run may attach to, with its project."""

        revision = await self.get_revision(organization_id, revision_id)
        project = await self.get_project(organization_id, revision.project_id)
        if project.status != ProjectStatus.ACTIVE.value:
            raise ProjectConflictError("The project is archived; runs cannot be added.")
        if revision.status != ProjectRevisionStatus.OPEN.value:
            raise ProjectConflictError("Runs can only be added to the open revision.")
        return project, revision

    # -- helpers --------------------------------------------------------------------------

    async def _commit_or_conflict(self, message: str) -> None:
        try:
            await self.repository.commit()
        except IntegrityError as exc:
            await self.repository.rollback()
            raise ProjectConflictError(message) from exc


__all__ = [
    "FIRST_REVISION_LABEL",
    "ProjectConflictError",
    "ProjectError",
    "ProjectNotFoundError",
    "ProjectService",
]
