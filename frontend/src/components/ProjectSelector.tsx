import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../app/authContext";
import { PROJECT_QUERY_KEY, useProject } from "../app/projectContext";
import {
  getProject,
  listProjects,
  type ProjectRevisionStatus,
  type ProjectDetail,
} from "../services/projects";

// The project the workspace is working in, chosen once in the shell topbar (EOS-01 b).
//
// Only the project is chosen here: the revision is always the open one, which the provider
// keeps up to date. Older revisions are read on the projects page, not from the topbar.
// A project without an open revision can still be chosen - it is then shown as read-only,
// and a study run made in that state belongs to no project.

export const PROJECT_LIST_QUERY_KEY = ["projects", "list", "ACTIVE"] as const;

const NO_PROJECT = "";
const REVISION_STATUS_LABELS: Record<ProjectRevisionStatus, string> = {
  OPEN: "Open",
  ISSUED: "Issued",
  SUPERSEDED: "Superseded",
};
const NO_OPEN_REVISION = "No open revision — new runs will not be linked to this project";
const LIST_FAILED = "Projects could not be loaded.";
const PROJECT_FAILED = "That project could not be opened.";

export function ProjectSelector() {
  const { state: authState } = useAuth();
  const { state, select, clear } = useProject();
  const queryClient = useQueryClient();
  const [failure, setFailure] = useState<string | null>(null);

  const signedIn = authState.status === "signed-in";
  const projectsQuery = useQuery({
    queryKey: PROJECT_LIST_QUERY_KEY,
    queryFn: ({ signal }) => listProjects("ACTIVE", signal),
    enabled: signedIn,
  });

  if (!signedIn) {
    return null;
  }

  const projects = projectsQuery.data ?? [];
  const chosenId =
    state.status === "selected" || state.status === "read-only" ? state.project.id : NO_PROJECT;

  async function choose(projectId: string): Promise<void> {
    setFailure(null);

    if (projectId === NO_PROJECT) {
      clear();
      return;
    }

    try {
      // The provider reads this project under the same key, so the detail is fetched once.
      const detail = await queryClient.fetchQuery<ProjectDetail>({
        queryKey: [...PROJECT_QUERY_KEY, projectId],
        queryFn: ({ signal }) => getProject(projectId, signal),
      });
      // Without an open revision the newest one is shown, and the provider makes it read-only.
      const revisionId = detail.open_revision_id ?? detail.revisions[0]?.id;

      if (revisionId === undefined) {
        setFailure(PROJECT_FAILED);
        return;
      }

      select(projectId, revisionId);
    } catch {
      setFailure(PROJECT_FAILED);
    }
  }

  const message = projectsQuery.isError ? LIST_FAILED : failure;

  return (
    <div data-shell-project>
      <label data-shell-project-label htmlFor="shell-project">
        Project
      </label>
      <select
        id="shell-project"
        value={chosenId}
        disabled={projectsQuery.isPending || projectsQuery.isError}
        onChange={(event) => void choose(event.target.value)}
      >
        <option value={NO_PROJECT}>No project (unassigned runs)</option>
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.code} — {project.name}
          </option>
        ))}
      </select>

      {state.status === "selected" || state.status === "read-only" ? (
        <span data-shell-project-revision>
          {state.revision.label} · {REVISION_STATUS_LABELS[state.revision.status]}
        </span>
      ) : null}

      {state.status === "read-only" ? (
        <span data-shell-project-hint>
          {NO_OPEN_REVISION}. <Link to="/projects">Projects</Link>
        </span>
      ) : null}

      {message !== null ? (
        <span data-shell-project-hint role="alert">
          {message}
        </span>
      ) : null}
    </div>
  );
}
