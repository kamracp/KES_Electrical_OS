import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import "../styles/projects.css";
import { useAuth } from "../app/authContext";
import { PROJECT_QUERY_KEY, useProject } from "../app/projectContext";
import {
  archiveProject,
  createProject,
  createRevision,
  createSite,
  getProject,
  issueRevision,
  jurisdictionProfileSchema,
  listProjects,
  listSites,
  updateProject,
  updateSite,
  type JurisdictionProfile,
  type NewProject,
  type NewSite,
  type Project,
  type ProjectRevision,
  type Site,
} from "../services/projects";

// Project configuration (EOS-01 b): the sites of the organization, its projects and the
// revisions a calculation run can be attached to.
//
// Every member reads this page; the server decides what may be written and answers 403 to
// anybody else, so the page only hides the actions a role cannot use. A project is never
// deleted: it is archived, and its issued revisions stay as the record of what was handed
// over. Codes, labels and names are shown exactly as the API returns them.

const SITES_KEY = ["projects", "sites"] as const;
const PROJECTS_KEY = ["projects", "list", "ALL"] as const;

const REVISION_STATUS_LABELS: Record<ProjectRevision["status"], string> = {
  OPEN: "Open",
  ISSUED: "Issued",
  SUPERSEDED: "Superseded",
};

type NewSiteDraft = { code: string; name: string; location: string };
type NewProjectDraft = {
  siteId: string;
  code: string;
  name: string;
  profile: JurisdictionProfile;
  clientName: string;
  description: string;
  firstRevisionLabel: string;
};

const EMPTY_SITE: NewSiteDraft = { code: "", name: "", location: "" };
const EMPTY_PROJECT: NewProjectDraft = {
  siteId: "",
  code: "",
  name: "",
  profile: "IN",
  clientName: "",
  description: "",
  firstRevisionLabel: "Rev 1",
};

/** Asked before a site stops taking new projects; existing ones are untouched. */
function switchOffQuestion(code: string): string {
  return (
    `Switch off site ${code}? It will take no new projects. ` +
    "Existing projects stay unchanged."
  );
}

function describeFailure(caught: unknown, fallback: string): string {
  return caught instanceof Error && caught.message.trim() !== "" ? caught.message : fallback;
}

function formatDateTime(value: string | null): string {
  if (value === null) {
    return "—";
  }

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function trimmedOrNull(value: string): string | null {
  const cleaned = value.trim();
  return cleaned === "" ? null : cleaned;
}

type PanelProps = {
  projectId: string;
  canWrite: boolean;
  canIssue: boolean;
  siteName: (siteId: string) => string;
  onChanged: (message: string) => void;
};

function ProjectDetailPanel({ projectId, canWrite, canIssue, siteName, onChanged }: PanelProps) {
  const queryClient = useQueryClient();
  const { select } = useProject();
  const [edit, setEdit] = useState<{ name: string; client: string; description: string } | null>(
    null,
  );
  const [revisionDraft, setRevisionDraft] = useState<{ label: string; notes: string } | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [revisionError, setRevisionError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const detailQuery = useQuery({
    queryKey: [...PROJECT_QUERY_KEY, projectId],
    queryFn: ({ signal }) => getProject(projectId, signal),
  });

  function reload(): Promise<void> {
    return queryClient.invalidateQueries({ queryKey: ["projects"] });
  }

  const updateMutation = useMutation({
    mutationFn: (change: { name?: string; client_name?: string | null; description?: string | null }) =>
      updateProject(projectId, change),
    onSuccess: reload,
  });
  const revisionMutation = useMutation({
    mutationFn: (revision: { label: string; notes?: string | null }) =>
      createRevision(projectId, revision),
    onSuccess: reload,
  });
  const issueMutation = useMutation({
    mutationFn: (revisionId: string) => issueRevision(projectId, revisionId),
    onSuccess: reload,
  });
  const archiveMutation = useMutation({
    mutationFn: () => archiveProject(projectId),
    onSuccess: reload,
  });

  if (detailQuery.isPending) {
    return (
      <section aria-label="Project detail">
        <h2>Project</h2>
        <p data-projects-note>Loading the project…</p>
      </section>
    );
  }

  if (detailQuery.isError || detailQuery.data === undefined) {
    return (
      <section aria-label="Project detail">
        <h2>Project</h2>
        <p role="alert">{describeFailure(detailQuery.error, "The project could not be loaded.")}</p>
      </section>
    );
  }

  const detail = detailQuery.data;
  const openRevisionId = detail.open_revision_id;
  const archived = detail.status === "ARCHIVED";
  const busy =
    updateMutation.isPending ||
    revisionMutation.isPending ||
    issueMutation.isPending ||
    archiveMutation.isPending;
  const draft = edit ?? {
    name: detail.name,
    client: detail.client_name ?? "",
    description: detail.description ?? "",
  };

  async function submitEdit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    if (draft.name.trim() === "") {
      setEditError("Project name is required.");
      return;
    }

    setEditError(null);

    try {
      await updateMutation.mutateAsync({
        name: draft.name.trim(),
        client_name: trimmedOrNull(draft.client),
        description: trimmedOrNull(draft.description),
      });
      setEdit(null);
      onChanged(`${detail.code} was changed.`);
    } catch (caught) {
      setEditError(describeFailure(caught, "The project was not changed."));
    }
  }

  async function submitRevision(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    if (revisionDraft === null) {
      return;
    }
    if (revisionDraft.label.trim() === "") {
      setRevisionError("Revision label is required.");
      return;
    }

    setRevisionError(null);

    try {
      const created = await revisionMutation.mutateAsync({
        label: revisionDraft.label.trim(),
        notes: trimmedOrNull(revisionDraft.notes),
      });
      setRevisionDraft(null);
      onChanged(`${created.label} is now the open revision of ${detail.code}.`);
    } catch (caught) {
      setRevisionError(describeFailure(caught, "The revision was not created."));
    }
  }

  async function issueOpenRevision(): Promise<void> {
    if (openRevisionId === null) {
      return;
    }

    setActionError(null);

    try {
      const issued = await issueMutation.mutateAsync(openRevisionId);
      onChanged(`${issued.label} of ${detail.code} was issued and is now frozen.`);
    } catch (caught) {
      setActionError(describeFailure(caught, "The revision was not issued."));
    }
  }

  async function archive(): Promise<void> {
    setActionError(null);

    try {
      await archiveMutation.mutateAsync();
      onChanged(`${detail.code} was archived; it takes no further runs.`);
    } catch (caught) {
      setActionError(describeFailure(caught, "The project was not archived."));
    }
  }

  return (
    <section aria-label="Project detail" data-project-id={detail.id}>
      <h2>
        {detail.code} — {detail.name}
      </h2>
      <p data-projects-note>
        Site {siteName(detail.site_id)} · Jurisdiction profile {detail.jurisdiction_profile} ·{" "}
        {archived ? "Archived" : "Active"}
        {detail.client_name !== null ? ` · Client ${detail.client_name}` : ""}
      </p>
      {detail.description !== null ? <p>{detail.description}</p> : null}

      <p data-projects-actions>
        <button
          type="button"
          disabled={openRevisionId === null}
          onClick={() => {
            if (openRevisionId !== null) {
              select(detail.id, openRevisionId);
              onChanged(`Studies are now saved in ${detail.code}.`);
            }
          }}
        >
          Use in studies
        </button>
        {canWrite && !archived ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => setRevisionDraft(revisionDraft === null ? { label: "", notes: "" } : null)}
          >
            New revision
          </button>
        ) : null}
        {canIssue && openRevisionId !== null ? (
          <button type="button" disabled={busy} onClick={() => void issueOpenRevision()}>
            Issue revision
          </button>
        ) : null}
        {canIssue && !archived ? (
          <button type="button" disabled={busy} onClick={() => void archive()}>
            Archive project
          </button>
        ) : null}
      </p>
      {openRevisionId === null ? (
        <p data-projects-note>
          No open revision: new studies are not linked to this project until a revision is opened.
        </p>
      ) : null}
      {actionError !== null ? <p role="alert">{actionError}</p> : null}

      {revisionDraft !== null ? (
        <form onSubmit={(event) => void submitRevision(event)} noValidate aria-label="New revision">
          <fieldset disabled={busy}>
            <legend>New revision</legend>
            <label>
              Label
              <input
                type="text"
                name="revision-label"
                value={revisionDraft.label}
                onChange={(event) =>
                  setRevisionDraft({ ...revisionDraft, label: event.target.value })
                }
              />
            </label>
            <label>
              Notes
              <input
                type="text"
                name="revision-notes"
                value={revisionDraft.notes}
                onChange={(event) =>
                  setRevisionDraft({ ...revisionDraft, notes: event.target.value })
                }
              />
            </label>
            <p data-projects-note>The revision that is open now becomes superseded.</p>
          </fieldset>
          {revisionError !== null ? <p role="alert">{revisionError}</p> : null}
          <button type="submit" disabled={busy}>
            {revisionMutation.isPending ? "Opening…" : "Open revision"}
          </button>
        </form>
      ) : null}

      {canWrite && !archived ? (
        <form onSubmit={(event) => void submitEdit(event)} noValidate aria-label="Edit project">
          <fieldset disabled={busy}>
            <legend>Edit project</legend>
            <label>
              Name
              <input
                type="text"
                name="project-name"
                value={draft.name}
                onChange={(event) => setEdit({ ...draft, name: event.target.value })}
              />
            </label>
            <label>
              Client
              <input
                type="text"
                name="project-client"
                value={draft.client}
                onChange={(event) => setEdit({ ...draft, client: event.target.value })}
              />
            </label>
            <label>
              Description
              <input
                type="text"
                name="project-description"
                value={draft.description}
                onChange={(event) => setEdit({ ...draft, description: event.target.value })}
              />
            </label>
          </fieldset>
          {editError !== null ? <p role="alert">{editError}</p> : null}
          <button type="submit" disabled={busy}>
            {updateMutation.isPending ? "Saving…" : "Save changes"}
          </button>
        </form>
      ) : null}

      <h3>Revisions</h3>
      <div data-table-scroll>
        <table>
          <thead>
            <tr>
              <th scope="col">No.</th>
              <th scope="col">Label</th>
              <th scope="col">Status</th>
              <th scope="col">Created by</th>
              <th scope="col">Issued by</th>
              <th scope="col">Issued at</th>
            </tr>
          </thead>
          <tbody>
            {detail.revisions.map((revision) => (
              <tr key={revision.id} data-revision-id={revision.id}>
                <th scope="row">{revision.revision_number}</th>
                <td>{revision.label}</td>
                <td>{REVISION_STATUS_LABELS[revision.status]}</td>
                <td>{revision.created_by ?? "—"}</td>
                <td>{revision.issued_by ?? "—"}</td>
                <td>{formatDateTime(revision.issued_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function ProjectsPage() {
  const { state } = useAuth();
  const queryClient = useQueryClient();
  const session = state.status === "signed-in" ? state.session : null;
  const canWrite = session?.role === "OWNER" || session?.role === "ENGINEER";
  const canIssue = session?.role === "OWNER";

  const [openProjectId, setOpenProjectId] = useState<string | null>(null);
  const [siteDraft, setSiteDraft] = useState<NewSiteDraft>(EMPTY_SITE);
  const [projectDraft, setProjectDraft] = useState<NewProjectDraft>(EMPTY_PROJECT);
  const [siteError, setSiteError] = useState<string | null>(null);
  const [projectError, setProjectError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const sitesQuery = useQuery({
    queryKey: SITES_KEY,
    queryFn: ({ signal }) => listSites(true, signal),
    enabled: session !== null,
  });
  const projectsQuery = useQuery({
    queryKey: PROJECTS_KEY,
    queryFn: ({ signal }) => listProjects(undefined, signal),
    enabled: session !== null,
  });

  function reload(): Promise<void> {
    // One key for the page, the topbar selector and the project provider alike.
    return queryClient.invalidateQueries({ queryKey: ["projects"] });
  }

  // Wrapped, not passed straight through: react-query hands the mutation function a second
  // argument of its own, which has no business in a request body.
  const siteMutation = useMutation({
    mutationFn: (site: NewSite) => createSite(site),
    onSuccess: reload,
  });
  const siteChangeMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      updateSite(id, { is_active: isActive }),
    onSuccess: reload,
  });
  const projectMutation = useMutation({
    mutationFn: (project: NewProject) => createProject(project),
    onSuccess: reload,
  });

  if (session === null) {
    return null;
  }

  const sites = sitesQuery.data ?? [];
  const activeSites = sites.filter((site) => site.is_active);
  const siteNames = new Map(sites.map((site) => [site.id, `${site.code} — ${site.name}`]));
  const busy = siteMutation.isPending || siteChangeMutation.isPending || projectMutation.isPending;

  function siteName(siteId: string): string {
    return siteNames.get(siteId) ?? "—";
  }

  async function submitSite(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setNotice(null);

    if (siteDraft.code.trim() === "" || siteDraft.name.trim() === "") {
      setSiteError("Site code and name are required.");
      return;
    }

    setSiteError(null);

    try {
      const created = await siteMutation.mutateAsync({
        code: siteDraft.code.trim(),
        name: siteDraft.name.trim(),
        location: trimmedOrNull(siteDraft.location),
      });
      setSiteDraft(EMPTY_SITE);
      setNotice(`Site ${created.code} was created.`);
    } catch (caught) {
      setSiteError(describeFailure(caught, "The site was not created."));
    }
  }

  async function switchSite(site: Site): Promise<void> {
    // Switching a site off is one click away from a list of sites, and it stops
    // every new project there, so it asks first. Switching one back on takes
    // nothing away and stays a single click.
    if (site.is_active && !window.confirm(switchOffQuestion(site.code))) {
      return;
    }

    setSiteError(null);
    setNotice(null);

    try {
      await siteChangeMutation.mutateAsync({ id: site.id, isActive: !site.is_active });
      setNotice(
        site.is_active
          ? `Site ${site.code} takes no new projects.`
          : `Site ${site.code} is in use again.`,
      );
    } catch (caught) {
      setSiteError(describeFailure(caught, "The site was not changed."));
    }
  }

  async function submitProject(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setNotice(null);

    if (projectDraft.siteId === "") {
      setProjectError("Choose the site of the project.");
      return;
    }
    if (projectDraft.code.trim() === "" || projectDraft.name.trim() === "") {
      setProjectError("Project code and name are required.");
      return;
    }

    setProjectError(null);

    try {
      const created = await projectMutation.mutateAsync({
        site_id: projectDraft.siteId,
        code: projectDraft.code.trim(),
        name: projectDraft.name.trim(),
        jurisdiction_profile: projectDraft.profile,
        client_name: trimmedOrNull(projectDraft.clientName),
        description: trimmedOrNull(projectDraft.description),
        first_revision_label: projectDraft.firstRevisionLabel.trim() || "Rev 1",
      });
      setProjectDraft(EMPTY_PROJECT);
      setOpenProjectId(created.id);
      setNotice(`Project ${created.code} was created with its first revision.`);
    } catch (caught) {
      setProjectError(describeFailure(caught, "The project was not created."));
    }
  }

  return (
    <main data-projects-page>
      <header>
        <p>EOS-01 · Project configuration</p>
        <h1>Projects</h1>
        <p>
          Sites, projects and revisions of {session.organization.name}. A study is saved in the
          open revision of the project chosen in the top bar; a project is archived, never
          deleted, and an issued revision stays as the record of what was handed over.
        </p>
      </header>

      {notice !== null ? <p role="status">{notice}</p> : null}

      <section aria-label="Sites">
        <h2>Sites</h2>

        {sitesQuery.isPending ? <p data-projects-note>Loading the sites…</p> : null}
        {sitesQuery.isError ? (
          <p role="alert">{describeFailure(sitesQuery.error, "The sites could not be loaded.")}</p>
        ) : null}
        {siteError !== null ? <p role="alert">{siteError}</p> : null}

        {sitesQuery.data !== undefined ? (
          sites.length === 0 ? (
            <p data-projects-note>No sites yet. Add the first one below.</p>
          ) : (
            <div data-table-scroll>
              <table>
                <thead>
                  <tr>
                    <th scope="col">Code</th>
                    <th scope="col">Name</th>
                    <th scope="col">Location</th>
                    <th scope="col">Status</th>
                    {canWrite ? <th scope="col">Actions</th> : null}
                  </tr>
                </thead>
                <tbody>
                  {sites.map((site) => (
                    <tr key={site.id} data-site-id={site.id} data-site-active={site.is_active}>
                      <th scope="row">{site.code}</th>
                      <td>{site.name}</td>
                      <td>{site.location ?? "—"}</td>
                      <td>{site.is_active ? "In use" : "Inactive"}</td>
                      {canWrite ? (
                        <td>
                          <button type="button" disabled={busy} onClick={() => void switchSite(site)}>
                            {site.is_active ? "Switch off" : "Switch on"}
                          </button>
                        </td>
                      ) : null}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : null}

        {canWrite ? (
          <form onSubmit={(event) => void submitSite(event)} noValidate aria-label="Add a site">
            <fieldset disabled={busy}>
              <legend>Add a site</legend>
              <label>
                Code
                <input
                  type="text"
                  name="site-code"
                  value={siteDraft.code}
                  onChange={(event) => setSiteDraft({ ...siteDraft, code: event.target.value })}
                />
              </label>
              <label>
                Name
                <input
                  type="text"
                  name="site-name"
                  value={siteDraft.name}
                  onChange={(event) => setSiteDraft({ ...siteDraft, name: event.target.value })}
                />
              </label>
              <label>
                Location
                <input
                  type="text"
                  name="site-location"
                  value={siteDraft.location}
                  onChange={(event) => setSiteDraft({ ...siteDraft, location: event.target.value })}
                />
              </label>
              <p data-projects-note>
                The code is used in project references: letters, digits, dot, dash or underscore,
                for example PLANT-A.
              </p>
            </fieldset>
            <button type="submit" disabled={busy}>
              {siteMutation.isPending ? "Adding…" : "Add site"}
            </button>
          </form>
        ) : null}
      </section>

      <section aria-label="Projects">
        <h2>Projects</h2>

        {projectsQuery.isPending ? <p data-projects-note>Loading the projects…</p> : null}
        {projectsQuery.isError ? (
          <p role="alert">
            {describeFailure(projectsQuery.error, "The projects could not be loaded.")}
          </p>
        ) : null}

        {projectsQuery.data !== undefined ? (
          projectsQuery.data.length === 0 ? (
            <p data-projects-note>No projects yet.</p>
          ) : (
            <div data-table-scroll>
              <table>
                <thead>
                  <tr>
                    <th scope="col">Code</th>
                    <th scope="col">Name</th>
                    <th scope="col">Client</th>
                    <th scope="col">Profile</th>
                    <th scope="col">Status</th>
                    <th scope="col">Site</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {projectsQuery.data.map((project: Project) => (
                    <tr
                      key={project.id}
                      data-project-id={project.id}
                      data-project-status={project.status}
                    >
                      <th scope="row">{project.code}</th>
                      <td>{project.name}</td>
                      <td>{project.client_name ?? "—"}</td>
                      <td>{project.jurisdiction_profile}</td>
                      <td>{project.status === "ACTIVE" ? "Active" : "Archived"}</td>
                      <td>{siteName(project.site_id)}</td>
                      <td>
                        <button
                          type="button"
                          onClick={() =>
                            setOpenProjectId(openProjectId === project.id ? null : project.id)
                          }
                        >
                          {openProjectId === project.id ? "Close" : "Open"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : null}

        {canWrite ? (
          <form
            onSubmit={(event) => void submitProject(event)}
            noValidate
            aria-label="Add a project"
          >
            <fieldset disabled={busy}>
              <legend>Add a project</legend>
              <label>
                Site
                <select
                  name="project-site"
                  value={projectDraft.siteId}
                  onChange={(event) =>
                    setProjectDraft({ ...projectDraft, siteId: event.target.value })
                  }
                >
                  <option value="">Choose a site</option>
                  {activeSites.map((site) => (
                    <option key={site.id} value={site.id}>
                      {site.code} — {site.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Code
                <input
                  type="text"
                  name="project-code"
                  value={projectDraft.code}
                  onChange={(event) =>
                    setProjectDraft({ ...projectDraft, code: event.target.value })
                  }
                />
              </label>
              <label>
                Name
                <input
                  type="text"
                  name="new-project-name"
                  value={projectDraft.name}
                  onChange={(event) =>
                    setProjectDraft({ ...projectDraft, name: event.target.value })
                  }
                />
              </label>
              <label>
                Jurisdiction profile
                <select
                  name="project-profile"
                  value={projectDraft.profile}
                  onChange={(event) =>
                    setProjectDraft({
                      ...projectDraft,
                      profile: jurisdictionProfileSchema.parse(event.target.value),
                    })
                  }
                >
                  {jurisdictionProfileSchema.options.map((profile) => (
                    <option key={profile} value={profile}>
                      {profile}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Client
                <input
                  type="text"
                  name="new-project-client"
                  value={projectDraft.clientName}
                  onChange={(event) =>
                    setProjectDraft({ ...projectDraft, clientName: event.target.value })
                  }
                />
              </label>
              <label>
                Description
                <input
                  type="text"
                  name="new-project-description"
                  value={projectDraft.description}
                  onChange={(event) =>
                    setProjectDraft({ ...projectDraft, description: event.target.value })
                  }
                />
              </label>
              <label>
                First revision label
                <input
                  type="text"
                  name="first-revision-label"
                  value={projectDraft.firstRevisionLabel}
                  onChange={(event) =>
                    setProjectDraft({ ...projectDraft, firstRevisionLabel: event.target.value })
                  }
                />
              </label>
              <p data-projects-note>
                The jurisdiction profile decides which references a study of this project is
                checked against; a study sent to this project must use the same profile.
              </p>
            </fieldset>
            {projectError !== null ? <p role="alert">{projectError}</p> : null}
            <button type="submit" disabled={busy}>
              {projectMutation.isPending ? "Creating…" : "Add project"}
            </button>
          </form>
        ) : null}
      </section>

      {openProjectId !== null ? (
        <ProjectDetailPanel
          key={openProjectId}
          projectId={openProjectId}
          canWrite={canWrite}
          canIssue={canIssue}
          siteName={siteName}
          onChanged={setNotice}
        />
      ) : null}
    </main>
  );
}
