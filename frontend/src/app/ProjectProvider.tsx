import { useCallback, useEffect, useMemo, useState, type PropsWithChildren } from "react";
import { useQuery } from "@tanstack/react-query";

import { ApiError } from "../services/http";
import { getProject, type ProjectDetail, type ProjectRevision } from "../services/projects";
import { useAuth } from "./authContext";
import {
  PROJECT_QUERY_KEY,
  PROJECT_SELECTION_STORAGE_KEY,
  ProjectContext,
  type ProjectContextValue,
  type ProjectState,
} from "./projectContext";

// Keeps the chosen project and revision for the whole application (EOS-01 b).
//
// Only the two ids are remembered, in sessionStorage: the names always come from the server,
// so nothing about a client or a project stays in the browser after the tab is closed. Every
// storage access is guarded - a private window may refuse it, and an application must not
// fall over because of that.
//
// The chosen revision is never silently emptied. When it is no longer open the provider
// follows the project to its open revision; when the project has none at all the choice
// stays visible as "read-only". The selection is dropped only when it has become
// meaningless: another user signs in, the session ends, or the project itself is gone (404)
// or belongs to another organization (403). A network failure changes nothing.

type Selection = { projectId: string; revisionId: string };

function readSelection(): Selection | null {
  try {
    const stored = window.sessionStorage.getItem(PROJECT_SELECTION_STORAGE_KEY);
    if (stored === null) {
      return null;
    }
    const parsed: unknown = JSON.parse(stored);
    if (typeof parsed !== "object" || parsed === null) {
      return null;
    }
    const { projectId, revisionId } = parsed as Partial<Selection>;
    if (typeof projectId !== "string" || typeof revisionId !== "string") {
      return null;
    }
    if (projectId === "" || revisionId === "") {
      return null;
    }
    return { projectId, revisionId };
  } catch {
    // Unreadable or damaged: the workspace simply starts without a project.
    return null;
  }
}

function writeSelection(selection: Selection): void {
  try {
    window.sessionStorage.setItem(PROJECT_SELECTION_STORAGE_KEY, JSON.stringify(selection));
  } catch {
    // The choice still holds for this page; it just will not survive a reload.
  }
}

function forgetSelection(): void {
  try {
    window.sessionStorage.removeItem(PROJECT_SELECTION_STORAGE_KEY);
  } catch {
    // Nothing to do: there is no other place the choice could be stored.
  }
}

/** The revision to show: the chosen one while it exists, otherwise the newest. */
function revisionToShow(detail: ProjectDetail, revisionId: string): ProjectRevision | null {
  return detail.revisions.find((item) => item.id === revisionId) ?? detail.revisions[0] ?? null;
}

function stateFor(detail: ProjectDetail, revisionId: string): ProjectState {
  const open = detail.revisions.find((item) => item.id === detail.open_revision_id);

  if (open !== undefined && detail.status === "ACTIVE") {
    // Either the chosen revision is the open one, or the work has moved on to it.
    return { status: "selected", project: detail, revision: open };
  }

  const revision = revisionToShow(detail, revisionId);

  return revision === null
    ? { status: "none" }
    : { status: "read-only", project: detail, revision };
}

function isGone(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 403);
}

export function ProjectProvider({ children }: PropsWithChildren) {
  const { state: authState } = useAuth();
  const [selection, setSelection] = useState<Selection | null>(() => readSelection());

  const signedInUserId = authState.status === "signed-in" ? authState.session.user.id : null;
  const [lastUserId, setLastUserId] = useState<string | null>(signedInUserId);

  // One user's project must never be shown to the next user of the same browser.
  useEffect(() => {
    if (signedInUserId === lastUserId) {
      return;
    }
    setLastUserId(signedInUserId);
    if (lastUserId !== null) {
      forgetSelection();
      setSelection(null);
    }
  }, [signedInUserId, lastUserId]);

  const projectId = selection?.projectId ?? null;

  const projectQuery = useQuery({
    queryKey: [...PROJECT_QUERY_KEY, projectId],
    queryFn: ({ signal }) => getProject(projectId as string, signal),
    enabled: projectId !== null && signedInUserId !== null,
  });

  const { data: detail, error } = projectQuery;

  // A project that is gone, or that belongs to another organization, cannot stay chosen.
  useEffect(() => {
    if (error !== null && isGone(error)) {
      forgetSelection();
      setSelection(null);
    }
  }, [error]);

  const select = useCallback((nextProjectId: string, revisionId: string): void => {
    const next = { projectId: nextProjectId, revisionId };
    writeSelection(next);
    setSelection(next);
  }, []);

  const clear = useCallback((): void => {
    forgetSelection();
    setSelection(null);
  }, []);

  const state = useMemo<ProjectState>(() => {
    if (selection === null || signedInUserId === null) {
      return { status: "none" };
    }
    if (detail === undefined || detail.id !== selection.projectId) {
      return { status: "loading" };
    }
    return stateFor(detail, selection.revisionId);
  }, [selection, signedInUserId, detail]);

  // The work followed the project to its open revision: remember that one instead.
  useEffect(() => {
    if (state.status !== "selected" || selection === null) {
      return;
    }
    if (state.revision.id !== selection.revisionId) {
      const next = { projectId: selection.projectId, revisionId: state.revision.id };
      writeSelection(next);
      setSelection(next);
    }
  }, [state, selection]);

  const activeRevisionId = useCallback(
    (): string | null => (state.status === "selected" ? state.revision.id : null),
    [state],
  );

  const value = useMemo<ProjectContextValue>(
    () => ({ state, select, clear, activeRevisionId }),
    [state, select, clear, activeRevisionId],
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}
