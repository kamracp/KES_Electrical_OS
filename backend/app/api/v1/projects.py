"""
Sites, projects and project revisions of the caller's organization (EOS-01 b).

The router is included with engineer_writes (app.api.router): every signed-in member reads,
OWNER and ENGINEER write. Archiving a project and issuing a revision are the two steps the
organization cannot take back, so they additionally need OWNER.

The organization never comes from the request body: it comes from the session, and the service
answers "not found" for a site, project or revision of another organization. Who did it is
recorded with the session label, as in the study runs.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.authentication import CurrentSession, OwnerSession
from app.api.dependencies import DatabaseSession
from app.models.project import Project, ProjectRevision, ProjectRevisionStatus, ProjectStatus
from app.repositories.project import ProjectRepository
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectRevisionCreateRequest,
    ProjectRevisionListResponse,
    ProjectRevisionResponse,
    ProjectUpdateRequest,
    SiteCreateRequest,
    SiteListResponse,
    SiteResponse,
    SiteUpdateRequest,
)
from app.services.project import ProjectConflictError, ProjectNotFoundError, ProjectService

router = APIRouter(tags=["Projects"])


def get_project_service(db: DatabaseSession) -> ProjectService:
    return ProjectService(ProjectRepository(db))


ProjectServiceDependency = Annotated[ProjectService, Depends(get_project_service)]


def _not_found(exc: ProjectNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _conflict(exc: ProjectConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _detail(project: Project, revisions: list[ProjectRevision]) -> ProjectDetailResponse:
    """A project with its revisions, newest first, and the one that still takes runs."""

    open_revision = next(
        (revision for revision in revisions if revision.status == ProjectRevisionStatus.OPEN.value),
        None,
    )
    return ProjectDetailResponse(
        **ProjectResponse.model_validate(project).model_dump(),
        revisions=[ProjectRevisionResponse.model_validate(revision) for revision in revisions],
        open_revision_id=open_revision.id if open_revision is not None else None,
    )


# -- sites --------------------------------------------------------------------------------


@router.get("/sites", response_model=SiteListResponse)
async def list_sites(
    identity: CurrentSession,
    service: ProjectServiceDependency,
    include_inactive: Annotated[bool, Query()] = False,
) -> SiteListResponse:
    """The sites of the caller's organization; inactive ones only when they are asked for."""

    sites = await service.list_sites(identity.organization.id, include_inactive=include_inactive)
    return SiteListResponse(items=[SiteResponse.model_validate(site) for site in sites])


@router.post("/sites", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    payload: SiteCreateRequest,
    identity: CurrentSession,
    service: ProjectServiceDependency,
) -> SiteResponse:
    """Add a site; its code is unique within the organization."""

    try:
        site = await service.create_site(
            identity.organization.id,
            code=payload.code,
            name=payload.name,
            location=payload.location,
        )
    except ProjectConflictError as exc:
        raise _conflict(exc) from exc
    return SiteResponse.model_validate(site)


@router.patch("/sites/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: UUID,
    payload: SiteUpdateRequest,
    identity: CurrentSession,
    service: ProjectServiceDependency,
) -> SiteResponse:
    """Rename a site, correct its location, or take it out of use; the code stays."""

    try:
        site = await service.update_site(
            identity.organization.id,
            site_id,
            name=payload.name,
            location=payload.location,
            is_active=payload.is_active,
        )
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except ProjectConflictError as exc:
        raise _conflict(exc) from exc
    return SiteResponse.model_validate(site)


# -- projects -----------------------------------------------------------------------------


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    identity: CurrentSession,
    service: ProjectServiceDependency,
    status: Annotated[ProjectStatus | None, Query()] = None,
) -> ProjectListResponse:
    """The projects of the caller's organization, newest first; filtered by status if asked."""

    projects = await service.list_projects(identity.organization.id, status=status)
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(project) for project in projects]
    )


@router.post("/projects", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    identity: CurrentSession,
    service: ProjectServiceDependency,
) -> ProjectDetailResponse:
    """Create a project at one of the organization's sites, together with its revision 1."""

    try:
        project, revision = await service.create_project(
            identity.organization.id,
            site_id=payload.site_id,
            code=payload.code,
            name=payload.name,
            jurisdiction_profile=payload.jurisdiction_profile,
            client_name=payload.client_name,
            description=payload.description,
            created_by=identity.label,
            first_revision_label=payload.first_revision_label,
        )
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except ProjectConflictError as exc:
        raise _conflict(exc) from exc
    return _detail(project, [revision])


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: UUID,
    identity: CurrentSession,
    service: ProjectServiceDependency,
) -> ProjectDetailResponse:
    """One project with its revisions, newest first, and the revision that takes new runs."""

    try:
        project = await service.get_project(identity.organization.id, project_id)
        revisions = await service.list_revisions(identity.organization.id, project_id)
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    return _detail(project, revisions)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdateRequest,
    identity: CurrentSession,
    service: ProjectServiceDependency,
) -> ProjectResponse:
    """Correct the name, the client or the description; an archived project is read-only."""

    try:
        project = await service.update_project(
            identity.organization.id,
            project_id,
            name=payload.name,
            client_name=payload.client_name,
            description=payload.description,
        )
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except ProjectConflictError as exc:
        raise _conflict(exc) from exc
    return ProjectResponse.model_validate(project)


@router.post("/projects/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: UUID,
    actor: OwnerSession,
    service: ProjectServiceDependency,
) -> ProjectResponse:
    """Close a project for good: no change, no new revision and no new run after this."""

    try:
        project = await service.archive_project(actor.organization.id, project_id)
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except ProjectConflictError as exc:
        raise _conflict(exc) from exc
    return ProjectResponse.model_validate(project)


# -- revisions ----------------------------------------------------------------------------


@router.get("/projects/{project_id}/revisions", response_model=ProjectRevisionListResponse)
async def list_revisions(
    project_id: UUID,
    identity: CurrentSession,
    service: ProjectServiceDependency,
) -> ProjectRevisionListResponse:
    """All revisions of a project, newest first."""

    try:
        revisions = await service.list_revisions(identity.organization.id, project_id)
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    return ProjectRevisionListResponse(
        items=[ProjectRevisionResponse.model_validate(revision) for revision in revisions]
    )


@router.post(
    "/projects/{project_id}/revisions",
    response_model=ProjectRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_revision(
    project_id: UUID,
    payload: ProjectRevisionCreateRequest,
    identity: CurrentSession,
    service: ProjectServiceDependency,
) -> ProjectRevisionResponse:
    """Open the next revision; the one that was open becomes superseded."""

    try:
        revision = await service.create_revision(
            identity.organization.id,
            project_id,
            label=payload.label,
            created_by=identity.label,
            notes=payload.notes,
        )
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except ProjectConflictError as exc:
        raise _conflict(exc) from exc
    return ProjectRevisionResponse.model_validate(revision)


@router.post(
    "/projects/{project_id}/revisions/{revision_id}/issue",
    response_model=ProjectRevisionResponse,
)
async def issue_revision(
    project_id: UUID,
    revision_id: UUID,
    actor: OwnerSession,
    service: ProjectServiceDependency,
) -> ProjectRevisionResponse:
    """Freeze the open revision as the issued record, signed with the owner's name."""

    try:
        revision = await service.get_revision(actor.organization.id, revision_id)
        if revision.project_id != project_id:
            raise ProjectNotFoundError("Revision not found.")
        revision = await service.issue_revision(
            actor.organization.id, revision_id, issued_by=actor.label
        )
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except ProjectConflictError as exc:
        raise _conflict(exc) from exc
    return ProjectRevisionResponse.model_validate(revision)
