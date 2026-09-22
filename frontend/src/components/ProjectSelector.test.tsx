// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue, type AuthState } from "../app/authContext";
import {
  ProjectContext,
  type ProjectContextValue,
  type ProjectState,
} from "../app/projectContext";
import { ApiError } from "../services/http";
import {
  getProject,
  listProjects,
  type Project,
  type ProjectDetail,
  type ProjectRevision,
} from "../services/projects";
import { ProjectSelector } from "./ProjectSelector";

vi.mock("../services/projects", () => ({ getProject: vi.fn(), listProjects: vi.fn() }));

const listProjectsMock = vi.mocked(listProjects);
const getProjectMock = vi.mocked(getProject);

const PROJECT_ID = "2a7d5c31-9b0e-4a21-8f6c-7d8e9f0a1b2c";
const OTHER_ID = "3b8e6d42-1c3f-4b5a-9e7d-8f9a0b1c2d3e";
const REVISION_1 = "4b8e6d42-1c3f-4b5a-9e7d-8f9a0b1c2d3e";
const REVISION_2 = "5c9f7e53-2d4a-4c6b-af8e-9a0b1c2d3e4f";

const SIGNED_IN: AuthState = {
  status: "signed-in",
  session: {
    user: {
      id: "7b0c0a3e-5d0e-4a53-9c58-0d1f6f2f7a11",
      email: "owner@example.com",
      full_name: "Test Owner",
      must_change_password: false,
    },
    organization: { id: "c1b7f1de-32a4-4c0b-8a4e-3f1f2a9d5b22", code: "KES", name: "KES" },
    role: "OWNER",
    session_expires_at: "2026-09-27T10:00:00Z",
    idle_timeout_minutes: 720,
  },
};

function project(id: string, code: string, name: string): Project {
  return {
    id,
    site_id: "6f1c9f1e-6a2b-4f5c-9b3d-1e2f3a4b5c6d",
    code,
    name,
    client_name: null,
    jurisdiction_profile: "IN",
    status: "ACTIVE",
    description: null,
    created_at: "2026-09-22T09:00:00Z",
    updated_at: "2026-09-22T09:00:00Z",
  };
}

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

const PUMP_HOUSE = project(PROJECT_ID, "PRJ-001", "Pump House");
const WORKSHOP = project(OTHER_ID, "PRJ-002", "Workshop");

function detail(overrides: Partial<ProjectDetail> = {}): ProjectDetail {
  return {
    ...PUMP_HOUSE,
    revisions: [revision(REVISION_1, 1, "OPEN")],
    open_revision_id: REVISION_1,
    ...overrides,
  };
}

function renderSelector(
  projectState: ProjectState,
  authState: AuthState = SIGNED_IN,
): { select: ProjectContextValue["select"]; clear: ProjectContextValue["clear"] } {
  const select = vi.fn();
  const clear = vi.fn();
  const auth: AuthContextValue = {
    state: authState,
    signIn: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  };
  const projectValue: ProjectContextValue = {
    state: projectState,
    select,
    clear,
    activeRevisionId: () => (projectState.status === "selected" ? projectState.revision.id : null),
  };
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <ProjectContext.Provider value={projectValue}>
          <MemoryRouter>
            <ProjectSelector />
          </MemoryRouter>
        </ProjectContext.Provider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );

  return { select, clear };
}

describe("ProjectSelector", () => {
  beforeEach(() => {
    listProjectsMock.mockReset();
    getProjectMock.mockReset();
    listProjectsMock.mockResolvedValue([PUMP_HOUSE, WORKSHOP]);
  });
  afterEach(cleanup);

  it("offers the active projects with working outside a project first", async () => {
    renderSelector({ status: "none" });

    const select = await screen.findByLabelText("Project");
    await waitFor(() => expect(select).not.toBeDisabled());
    expect(
      [...(select as HTMLSelectElement).options].map((option) => option.textContent),
    ).toEqual(["No project (unassigned runs)", "PRJ-001 — Pump House", "PRJ-002 — Workshop"]);
    expect((select as HTMLSelectElement).value).toBe("");
  });

  it("selects the open revision of the project that was chosen", async () => {
    getProjectMock.mockResolvedValue(detail());
    const { select } = renderSelector({ status: "none" });
    const control = await screen.findByLabelText("Project");
    await waitFor(() => expect(control).not.toBeDisabled());

    fireEvent.change(control, { target: { value: PROJECT_ID } });

    await waitFor(() => expect(select).toHaveBeenCalledWith(PROJECT_ID, REVISION_1));
    expect(getProjectMock).toHaveBeenCalledTimes(1);
  });

  it("still selects a project whose last revision was issued", async () => {
    getProjectMock.mockResolvedValue(
      detail({ revisions: [revision(REVISION_2, 2, "ISSUED")], open_revision_id: null }),
    );
    const { select } = renderSelector({ status: "none" });
    const control = await screen.findByLabelText("Project");
    await waitFor(() => expect(control).not.toBeDisabled());

    fireEvent.change(control, { target: { value: PROJECT_ID } });

    await waitFor(() => expect(select).toHaveBeenCalledWith(PROJECT_ID, REVISION_2));
  });

  it("works outside a project again when that is chosen", async () => {
    const { clear } = renderSelector({
      status: "selected",
      project: PUMP_HOUSE,
      revision: revision(REVISION_1, 1, "OPEN"),
    });
    const control = await screen.findByLabelText("Project");
    await waitFor(() => expect(control).not.toBeDisabled());

    fireEvent.change(control, { target: { value: "" } });

    expect(clear).toHaveBeenCalledTimes(1);
    expect(getProjectMock).not.toHaveBeenCalled();
  });

  it("names the revision the runs are attached to", async () => {
    renderSelector({
      status: "selected",
      project: PUMP_HOUSE,
      revision: revision(REVISION_2, 2, "OPEN"),
    });

    expect(await screen.findByText("Rev 2 · Open")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Projects" })).not.toBeInTheDocument();
  });

  it("says plainly when a chosen project takes no runs, and offers the projects page", async () => {
    renderSelector({
      status: "read-only",
      project: PUMP_HOUSE,
      revision: revision(REVISION_1, 1, "ISSUED"),
    });

    expect(await screen.findByText("Rev 1 · Issued")).toBeInTheDocument();
    expect(
      screen.getByText(/No open revision — new runs will not be linked to this project/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Projects" })).toHaveAttribute("href", "/projects");
  });

  it("shows nothing at all while nobody is signed in", () => {
    const { container } = render(
      <QueryClientProvider client={new QueryClient()}>
        <AuthContext.Provider
          value={{
            state: { status: "signed-out" },
            signIn: vi.fn(),
            signOut: vi.fn(),
            refresh: vi.fn(),
          }}
        >
          <ProjectContext.Provider
            value={{
              state: { status: "none" },
              select: vi.fn(),
              clear: vi.fn(),
              activeRevisionId: () => null,
            }}
          >
            <MemoryRouter>
              <ProjectSelector />
            </MemoryRouter>
          </ProjectContext.Provider>
        </AuthContext.Provider>
      </QueryClientProvider>,
    );

    expect(container).toBeEmptyDOMElement();
    expect(listProjectsMock).not.toHaveBeenCalled();
  });

  it("keeps the topbar usable when the project list cannot be loaded", async () => {
    listProjectsMock.mockRejectedValue(new ApiError("The project list could not be loaded", 500));
    renderSelector({ status: "none" });

    expect(await screen.findByRole("alert")).toHaveTextContent("Projects could not be loaded.");
    expect(screen.getByLabelText("Project")).toBeDisabled();
  });

  it("says so when the chosen project cannot be opened", async () => {
    getProjectMock.mockRejectedValue(new ApiError("Project not found.", 404));
    renderSelector({ status: "none" });
    const control = await screen.findByLabelText("Project");
    await waitFor(() => expect(control).not.toBeDisabled());

    fireEvent.change(control, { target: { value: PROJECT_ID } });

    expect(await screen.findByRole("alert")).toHaveTextContent("That project could not be opened.");
  });
});
