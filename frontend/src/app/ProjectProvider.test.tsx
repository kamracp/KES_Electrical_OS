// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../services/http";
import { getProject, type ProjectDetail, type ProjectRevision } from "../services/projects";
import { AuthContext, type AuthContextValue, type AuthState } from "./authContext";
import { ProjectProvider } from "./ProjectProvider";
import { PROJECT_SELECTION_STORAGE_KEY, useProject } from "./projectContext";

vi.mock("../services/projects", () => ({ getProject: vi.fn() }));

const getProjectMock = vi.mocked(getProject);

const PROJECT_ID = "2a7d5c31-9b0e-4a21-8f6c-7d8e9f0a1b2c";
const REVISION_1 = "4b8e6d42-1c3f-4b5a-9e7d-8f9a0b1c2d3e";
const REVISION_2 = "5c9f7e53-2d4a-4c6b-af8e-9a0b1c2d3e4f";
const USER_ID = "7b0c0a3e-5d0e-4a53-9c58-0d1f6f2f7a11";

function revision(id: string, number: number, status: ProjectRevision["status"]): ProjectRevision {
  return {
    id,
    project_id: PROJECT_ID,
    revision_number: number,
    label: `Rev ${number}`,
    status,
    created_by: null,
    issued_by: null,
    issued_at: null,
    notes: null,
    created_at: "2026-09-22T09:00:00Z",
  };
}

function detail(overrides: Partial<ProjectDetail> = {}): ProjectDetail {
  return {
    id: PROJECT_ID,
    site_id: "6f1c9f1e-6a2b-4f5c-9b3d-1e2f3a4b5c6d",
    code: "PRJ-001",
    name: "Pump House",
    client_name: "Northern Mills",
    jurisdiction_profile: "IN",
    status: "ACTIVE",
    description: null,
    created_at: "2026-09-22T09:00:00Z",
    updated_at: "2026-09-22T09:00:00Z",
    revisions: [revision(REVISION_1, 1, "OPEN")],
    open_revision_id: REVISION_1,
    ...overrides,
  };
}

function session(userId = USER_ID): AuthState {
  return {
    status: "signed-in",
    session: {
      user: { id: userId, email: "owner@example.com", full_name: "Test Owner", must_change_password: false },
      organization: { id: "c1b7f1de-32a4-4c0b-8a4e-3f1f2a9d5b22", code: "KES", name: "KES" },
      role: "OWNER",
      session_expires_at: "2026-09-27T10:00:00Z",
      idle_timeout_minutes: 720,
    },
  };
}

function Probe() {
  const { state, select, clear, activeRevisionId } = useProject();

  return (
    <div>
      <p data-testid="status">{state.status}</p>
      <p data-testid="project">
        {state.status === "selected" || state.status === "read-only" ? state.project.code : ""}
      </p>
      <p data-testid="revision">
        {state.status === "selected" || state.status === "read-only" ? state.revision.label : ""}
      </p>
      <p data-testid="active">{activeRevisionId() ?? "none"}</p>
      <button type="button" onClick={() => select(PROJECT_ID, REVISION_1)}>
        select
      </button>
      <button type="button" onClick={clear}>
        clear
      </button>
    </div>
  );
}

function tree(authState: AuthState, queryClient: QueryClient) {
  const auth: AuthContextValue = {
    state: authState,
    signIn: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  };

  return (
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <ProjectProvider>
          <Probe />
        </ProjectProvider>
      </AuthContext.Provider>
    </QueryClientProvider>
  );
}

/** Render the workspace; signIn(state) then changes the session without remounting. */
function renderWith(authState: AuthState) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
  const rendered = render(tree(authState, queryClient));

  return {
    ...rendered,
    signIn: (next: AuthState) => rendered.rerender(tree(next, queryClient)),
  };
}

function stored(): unknown {
  const raw = window.sessionStorage.getItem(PROJECT_SELECTION_STORAGE_KEY);
  return raw === null ? null : JSON.parse(raw);
}

describe("ProjectProvider", () => {
  beforeEach(() => {
    getProjectMock.mockReset();
    window.sessionStorage.clear();
  });
  afterEach(() => {
    cleanup();
  });

  it("keeps the chosen revision across a remount and stores only the two ids", async () => {
    getProjectMock.mockResolvedValue(detail());

    const first = renderWith(session());
    screen.getByRole("button", { name: "select" }).click();

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("selected"));
    expect(screen.getByTestId("project").textContent).toBe("PRJ-001");
    expect(stored()).toEqual({ projectId: PROJECT_ID, revisionId: REVISION_1 });
    first.unmount();

    renderWith(session());

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("selected"));
    expect(screen.getByTestId("active").textContent).toBe(REVISION_1);
  });

  it("follows the project to its open revision when the chosen one was issued", async () => {
    window.sessionStorage.setItem(
      PROJECT_SELECTION_STORAGE_KEY,
      JSON.stringify({ projectId: PROJECT_ID, revisionId: REVISION_1 }),
    );
    getProjectMock.mockResolvedValue(
      detail({
        revisions: [revision(REVISION_2, 2, "OPEN"), revision(REVISION_1, 1, "ISSUED")],
        open_revision_id: REVISION_2,
      }),
    );

    renderWith(session());

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("selected"));
    expect(screen.getByTestId("revision").textContent).toBe("Rev 2");
    expect(screen.getByTestId("active").textContent).toBe(REVISION_2);
    await waitFor(() =>
      expect(stored()).toEqual({ projectId: PROJECT_ID, revisionId: REVISION_2 }),
    );
  });

  it("keeps an archived project on screen as read-only and attaches no run to it", async () => {
    window.sessionStorage.setItem(
      PROJECT_SELECTION_STORAGE_KEY,
      JSON.stringify({ projectId: PROJECT_ID, revisionId: REVISION_1 }),
    );
    getProjectMock.mockResolvedValue(
      detail({
        status: "ARCHIVED",
        revisions: [revision(REVISION_1, 1, "SUPERSEDED")],
        open_revision_id: null,
      }),
    );

    renderWith(session());

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("read-only"));
    expect(screen.getByTestId("project").textContent).toBe("PRJ-001");
    expect(screen.getByTestId("active").textContent).toBe("none");
    expect(stored()).not.toBeNull();
  });

  it("stays read-only when the last revision was issued and no successor was opened", async () => {
    window.sessionStorage.setItem(
      PROJECT_SELECTION_STORAGE_KEY,
      JSON.stringify({ projectId: PROJECT_ID, revisionId: REVISION_1 }),
    );
    getProjectMock.mockResolvedValue(
      detail({ revisions: [revision(REVISION_1, 1, "ISSUED")], open_revision_id: null }),
    );

    renderWith(session());

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("read-only"));
    expect(screen.getByTestId("revision").textContent).toBe("Rev 1");
    expect(screen.getByTestId("active").textContent).toBe("none");
  });

  it("empties the selection and the storage when the user asks for it", async () => {
    getProjectMock.mockResolvedValue(detail());
    renderWith(session());
    screen.getByRole("button", { name: "select" }).click();
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("selected"));

    screen.getByRole("button", { name: "clear" }).click();

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("none"));
    expect(stored()).toBeNull();
  });

  it("drops the selection when the session ends or another user signs in", async () => {
    window.sessionStorage.setItem(
      PROJECT_SELECTION_STORAGE_KEY,
      JSON.stringify({ projectId: PROJECT_ID, revisionId: REVISION_1 }),
    );
    getProjectMock.mockResolvedValue(detail());
    const workspace = renderWith(session());
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("selected"));

    // Sign-out: the same tab, the same provider, no project any more.
    workspace.signIn({ status: "signed-out" });

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("none"));
    expect(stored()).toBeNull();

    // And the next user starts empty, not in the project of the one before.
    workspace.signIn(session("11111111-2222-3333-4444-555555555555"));

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("none"));
    expect(stored()).toBeNull();
  });

  it("drops the selection when the project is gone or belongs to another organization", async () => {
    window.sessionStorage.setItem(
      PROJECT_SELECTION_STORAGE_KEY,
      JSON.stringify({ projectId: PROJECT_ID, revisionId: REVISION_1 }),
    );
    getProjectMock.mockRejectedValue(new ApiError("Project not found.", 404));

    renderWith(session());

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("none"));
    expect(stored()).toBeNull();
  });

  it("keeps the selection when the project could not be loaded this time", async () => {
    window.sessionStorage.setItem(
      PROJECT_SELECTION_STORAGE_KEY,
      JSON.stringify({ projectId: PROJECT_ID, revisionId: REVISION_1 }),
    );
    getProjectMock.mockRejectedValue(new ApiError("The project could not be loaded", 500));

    renderWith(session());

    await waitFor(() => expect(getProjectMock).toHaveBeenCalled());
    expect(screen.getByTestId("status").textContent).toBe("loading");
    expect(stored()).not.toBeNull();
  });

  it("ignores a damaged storage value and starts without a project", async () => {
    window.sessionStorage.setItem(PROJECT_SELECTION_STORAGE_KEY, "{not json");

    renderWith(session());

    expect(screen.getByTestId("status").textContent).toBe("none");
    expect(getProjectMock).not.toHaveBeenCalled();
  });

  it("shows no project while nobody is signed in", async () => {
    window.sessionStorage.setItem(
      PROJECT_SELECTION_STORAGE_KEY,
      JSON.stringify({ projectId: PROJECT_ID, revisionId: REVISION_1 }),
    );

    renderWith({ status: "signed-out" });

    expect(screen.getByTestId("status").textContent).toBe("none");
    expect(getProjectMock).not.toHaveBeenCalled();
  });
});
