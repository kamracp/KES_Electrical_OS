"""
Project spine models (EOS-01 b): sites, projects and project revisions.

An organization (identity.py) owns sites; a project belongs to an organization and to one of
its sites and states the jurisdiction profile it is designed under (GAP-004); a project has
numbered revisions and calculation runs are linked to one revision. Status-like values are text
with a CHECK constraint built from the Python enum, as in identity.py and calculation_runs.

Rules that span tables are enforced by the project service, not here: a project's site must
belong to the project's organization, and a project has exactly one OPEN revision at a time.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.electrical.jurisdiction import JurisdictionProfile


class ProjectStatus(StrEnum):
    """Lifecycle of a project."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ProjectRevisionStatus(StrEnum):
    """Lifecycle of one project revision."""

    OPEN = "OPEN"
    ISSUED = "ISSUED"
    SUPERSEDED = "SUPERSEDED"


def _in_list(column: str, members: type[StrEnum]) -> str:
    quoted = ", ".join(f"'{member.value}'" for member in members)
    return f"{column} IN ({quoted})"


class Site(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A physical location of an organization: a plant, a building, a campus."""

    __tablename__ = "sites"

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="sites_organization_code_unique"),
        CheckConstraint("code <> '' AND name <> ''", name="code_name_not_blank"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An engineering project at one site, designed under one jurisdiction profile."""

    __tablename__ = "projects"

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="projects_organization_code_unique"),
        CheckConstraint("code <> '' AND name <> ''", name="code_name_not_blank"),
        CheckConstraint(
            _in_list("jurisdiction_profile", JurisdictionProfile), name="jurisdiction_valid"
        ),
        CheckConstraint(_in_list("status", ProjectStatus), name="status_valid"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(200))
    jurisdiction_profile: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ProjectStatus.ACTIVE.value, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)


class ProjectRevision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    One numbered revision of a project.

    Calculation runs are linked to a revision; an ISSUED revision is the record of what was
    handed over and is never reopened, a later revision supersedes it.
    """

    __tablename__ = "project_revisions"

    __table_args__ = (
        UniqueConstraint(
            "project_id", "revision_number", name="project_revisions_project_number_unique"
        ),
        CheckConstraint("revision_number > 0", name="revision_positive"),
        CheckConstraint("label <> ''", name="label_not_blank"),
        CheckConstraint(_in_list("status", ProjectRevisionStatus), name="status_valid"),
        CheckConstraint(
            "status <> 'ISSUED' OR (issued_by IS NOT NULL AND issued_at IS NOT NULL)",
            name="issued_audit_complete",
        ),
    )

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ProjectRevisionStatus.OPEN.value, nullable=False, index=True
    )
    created_by: Mapped[str | None] = mapped_column(String(200))
    issued_by: Mapped[str | None] = mapped_column(String(200))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


__all__ = [
    "Project",
    "ProjectRevision",
    "ProjectRevisionStatus",
    "ProjectStatus",
    "Site",
]
