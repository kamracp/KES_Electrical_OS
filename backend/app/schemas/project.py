"""
Request and response schemas for the project spine (EOS-01 b).

Requests refuse unknown fields and clean their text before the service sees it: names and
labels lose their outer and inner extra spaces, optional text becomes None when it is blank,
and a code must be a short machine-friendly token so that it can be typed, sorted and used in
a document number. The rules that need the database - unique codes, one open revision, the
site belonging to the organization - stay in app.services.project.

Responses name their fields one by one and read straight from the ORM records. The
organization is never repeated: a caller only ever sees its own organization's records.
"""

import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.domain.electrical.jurisdiction import JurisdictionProfile
from app.models.project import ProjectRevisionStatus, ProjectStatus

CODE_MAX_LENGTH = 40
NAME_MAX_LENGTH = 200
LABEL_MAX_LENGTH = 100
LINE_MAX_LENGTH = 200
TEXT_MAX_LENGTH = 4000

# The label of the revision that is created together with the project; it mirrors
# FIRST_REVISION_LABEL in app.services.project, which schemas must not import (services
# import schemas).
DEFAULT_FIRST_REVISION_LABEL = "Rev 1"

_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_CODE_MESSAGE = "Use letters, digits, dot, dash or underscore, for example PRJ-001."


def _clean_code(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Code is required.")
    if len(cleaned) > CODE_MAX_LENGTH:
        raise ValueError(f"Code must have at most {CODE_MAX_LENGTH} characters.")
    if _CODE_PATTERN.fullmatch(cleaned) is None:
        raise ValueError(_CODE_MESSAGE)
    return cleaned


def _clean_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("Name is required.")
    if len(cleaned) > NAME_MAX_LENGTH:
        raise ValueError(f"Name must have at most {NAME_MAX_LENGTH} characters.")
    return cleaned


def _clean_label(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("Label is required.")
    if len(cleaned) > LABEL_MAX_LENGTH:
        raise ValueError(f"Label must have at most {LABEL_MAX_LENGTH} characters.")
    return cleaned


def _clean_line(value: str | None) -> str | None:
    """One line of optional text: a blank entry is the same as no entry at all."""

    if value is None:
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    if len(cleaned) > LINE_MAX_LENGTH:
        raise ValueError(f"Use at most {LINE_MAX_LENGTH} characters.")
    return cleaned


def _clean_text(value: str | None) -> str | None:
    """Free text: only the outer whitespace goes, paragraphs are kept as they were typed."""

    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > TEXT_MAX_LENGTH:
        raise ValueError(f"Use at most {TEXT_MAX_LENGTH} characters.")
    return cleaned


# The Field maxima only keep absurd request bodies away from the validators, which give the
# readable message and enforce the real column limits.
ResourceCode = Annotated[str, Field(max_length=200), AfterValidator(_clean_code)]
ResourceName = Annotated[str, Field(max_length=400), AfterValidator(_clean_name)]
RevisionLabel = Annotated[str, Field(max_length=200), AfterValidator(_clean_label)]
OptionalLine = Annotated[str | None, Field(max_length=400), AfterValidator(_clean_line)]
OptionalText = Annotated[str | None, Field(max_length=8000), AfterValidator(_clean_text)]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


# -- requests -----------------------------------------------------------------------------


class SiteCreateRequest(_Request):
    """A new site of the caller's organization; the code is unique within it."""

    code: ResourceCode
    name: ResourceName
    location: OptionalLine = None


class SiteUpdateRequest(_Request):
    """Only the fields that are sent are changed; the code of a site never changes."""

    name: ResourceName | None = None
    location: OptionalLine = None
    is_active: bool | None = None


class ProjectCreateRequest(_Request):
    """A new project at one site; the service creates revision 1 with it."""

    site_id: UUID
    code: ResourceCode
    name: ResourceName
    jurisdiction_profile: JurisdictionProfile
    client_name: OptionalLine = None
    description: OptionalText = None
    first_revision_label: RevisionLabel = DEFAULT_FIRST_REVISION_LABEL


class ProjectUpdateRequest(_Request):
    """Only the fields that are sent are changed; code, site and jurisdiction stay as they are."""

    name: ResourceName | None = None
    client_name: OptionalLine = None
    description: OptionalText = None


class ProjectRevisionCreateRequest(_Request):
    """The next revision of a project; the open one, if any, becomes superseded."""

    label: RevisionLabel
    notes: OptionalText = None


# -- responses ----------------------------------------------------------------------------


class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    location: str | None
    is_active: bool
    created_at: datetime


class SiteListResponse(BaseModel):
    items: list[SiteResponse]


class ProjectRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    revision_number: int
    label: str
    status: ProjectRevisionStatus
    created_by: str | None
    issued_by: str | None
    issued_at: datetime | None
    notes: str | None
    created_at: datetime


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    site_id: UUID
    code: str
    name: str
    client_name: str | None
    jurisdiction_profile: JurisdictionProfile
    status: ProjectStatus
    description: str | None
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    """One project with its revisions, newest first, and the revision that still takes runs."""

    revisions: list[ProjectRevisionResponse]
    open_revision_id: UUID | None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]


class ProjectRevisionListResponse(BaseModel):
    items: list[ProjectRevisionResponse]


class ProjectRevisionSummary(BaseModel):
    """The project and revision a calculation run belongs to, carried by the run responses."""

    model_config = ConfigDict(from_attributes=True)

    revision_id: UUID
    revision_number: int
    revision_label: str
    project_id: UUID
    project_code: str
    project_name: str


__all__ = [
    "CODE_MAX_LENGTH",
    "DEFAULT_FIRST_REVISION_LABEL",
    "LABEL_MAX_LENGTH",
    "LINE_MAX_LENGTH",
    "NAME_MAX_LENGTH",
    "TEXT_MAX_LENGTH",
    "ProjectCreateRequest",
    "ProjectDetailResponse",
    "ProjectListResponse",
    "ProjectResponse",
    "ProjectRevisionCreateRequest",
    "ProjectRevisionListResponse",
    "ProjectRevisionResponse",
    "ProjectRevisionSummary",
    "ProjectUpdateRequest",
    "SiteCreateRequest",
    "SiteListResponse",
    "SiteResponse",
    "SiteUpdateRequest",
]
