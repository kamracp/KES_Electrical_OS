import { createContext, useContext } from "react";

import type { Project, ProjectRevision } from "../services/projects";

// The project and revision the workspace is currently working in (EOS-01 b).
//
// "selected" means the revision is open and a new calculation run may be attached to it;
// "read-only" means the chosen project is still on screen but has no open revision any more
// (it was archived, or its revision was issued and no successor was opened), so a study run
// belongs to no project until the user picks another revision. Only these two carry a
// project and a revision, so a page never has to check for null.

export type ProjectState =
  | { status: "none" }
  | { status: "loading" }
  | { status: "selected"; project: Project; revision: ProjectRevision }
  | { status: "read-only"; project: Project; revision: ProjectRevision };

export type ProjectContextValue = {
  state: ProjectState;
  /** Work in this revision of this project; the choice survives a page reload. */
  select: (projectId: string, revisionId: string) => void;
  /** Work outside any project again; only the user empties the selection. */
  clear: () => void;
  /**
   * The revision a new run may be attached to, or null.
   *
   * Study forms send exactly this: in "read-only" it is null, so the run is stored without
   * a project instead of being refused by the server.
   */
  activeRevisionId: () => string | null;
};

/** react-query key of one project detail; the provider reloads it when the session changes. */
export const PROJECT_QUERY_KEY = ["projects", "detail"] as const;

/** The one browser key: two ids, never a project or client name. */
export const PROJECT_SELECTION_STORAGE_KEY = "keos.project-selection";

export const ProjectContext = createContext<ProjectContextValue | null>(null);

export function useProject(): ProjectContextValue {
  const value = useContext(ProjectContext);

  if (value === null) {
    throw new Error("useProject must be used inside <ProjectProvider>.");
  }

  return value;
}
