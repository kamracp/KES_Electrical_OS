// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../app/authContext";
import { ProjectContext, type ProjectContextValue } from "../app/projectContext";
import type { OrganizationRole, Session } from "../services/auth";
import { ApiError } from "../services/http";
import {
  archiveProject,
  createProject,
  createRevision,
  createSite,
  getProject,
  issueRevision,
  listProjects,
  listSites,
  updateProject,
  updateSite,
  type Project,
  type ProjectDetail,
  type ProjectRevision,
  type Site,
} from "../services/projects";
import { ProjectsPage } from "./ProjectsPage";

vi.mock("../services/projects", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/projects")>();
  return {
    ...actual,
    archiveProject: vi.fn(),
    createProject: vi.fn(),
    createRevision: vi.fn(),
    createSite: vi.fn(),
    getProject: vi.fn(),
    issueRevision: vi.fn(),
    listProjects: vi.fn(),
    listSites: vi.fn(),
    updateProject: vi.fn(),
    updateSite: vi.fn(),
  };
});

const listSitesMock = vi.mocked(listSites);
const listProjectsMock = vi.mocked(listProjects);
const getProjectMock = vi.mocked(getProject);
const createSiteMock = vi.mocked(createSite);
const createProjectMock = vi.mocked(createProject);
const updateSiteMock = vi.mocked(updateSite);
const createRevisionMock = vi.mocked(createRevision);
const issueRevisionMock = vi.mocked(issueRevision);
const archiveProjectMock = vi.mocked(archiveProject);
const updateProjectMock = vi.mocked(updateProject);

const SITE_ID = "6f1c9f1e-6a2b-4f5c-9b3d-1e2f3a4b5c6d";
const CLOSED_SITE_ID = "7a2d0b2f-7b3c-4c6d-8e4f-2f3a4b5c6d7e";
const PROJECT_ID = "2a7d5c31-9b0e-4a21-8f6c-7d8e9f0a1b2c";
const REVISION_1 = "4b8e6d42-1c3f-4b5a-9e7d-8f9a0b1c2d3e";
const REVISION_2 = "5c9f7e53-2d4a-4c6b-af8e-9a0b1c2d3e4f";

const SITE: Site = {
  id: SITE_ID,
  code: "PLANT-A",
  name: "Plant A",
  location: "Ludhiana",
  is_active: true,
  created_at: "2026-09-22T09:00:00Z",
};

const CLOSED_SITE: Site = {
  ...SITE,
  id: CLOSED_SITE_ID,
  code: "PLANT-B",
  name: "Plant B",
  location: null,
  is_active: false,
};

const PROJECT: Project = {
  id: PROJECT_ID,
  site_id: SITE_ID,
  code: "PRJ-001",
  name: "Pump House",
  client_name: "Northern Mills",
  jurisdiction_profile: "IN",
  status: "ACTIVE",
  description: null,
  created_at: "2026-09-22T09:00:00Z",
  updated_at: "2026-09-22T09:00:00Z",
};

function revision(
  id: string,
  number: number,
  status: ProjectRevision["status"],
): ProjectRevision {
  return {
    id,
    project_id: PROJECT_ID,
    revision_number: number,
    label: `Rev ${number}`,
    status,
    created_by: "Test Owner (owner@example.com)",
    issued_by: status === "ISSUED" ? "Test Owner (owner@example.com)" : null,
    issued_at: status === "ISSUED" ? "2026-09-22T10:00:00Z" : null,
    notes: null,
    created_at: "2026-09-22T09:00:00Z",
  };
}

function detail(overrides: Partial<ProjectDetail> = {}): ProjectDetail {
  return {
    ...PROJECT,
    revisions: [revision(REVISION_2, 2, "OPEN"), revision(REVISION_1, 1, "SUPERSEDED")],
    open_revision_id: REVISION_2,
    ...overrides,
  };
}

function sessionOf(role: OrganizationRole): Session {
  return {
    user: {
      id: "7b0c0a3e-5d0e-4a53-9c58-0d1f6f2f7a11",
      email: "owner@example.com",
      full_name: "Test Owner",
      must_change_password: false,
    },
    organization: { id: "c1b7f1de-32a4-4c0b-8a4e-3f1f2a9d5b22", code: "KES", name: "KES Works" },
    role,
    session_expires_at: "2026-09-27T10:00:00Z",
    idle_timeout_minutes: 720,
  };
}

function renderPage(role: OrganizationRole = "OWNER"): { select: ProjectContextValue["select"] } {
  const select = vi.fn();
  const auth: AuthContextValue = {
    state: { status: "signed-in", session: sessionOf(role) },
    signIn: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  };
  const projectValue: ProjectContextValue = {
    state: { status: "none" },
    select,
    clear: vi.fn(),
    activeRevisionId: () => null,
  };
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <ProjectContext.Provider value={projectValue}>
          <ProjectsPage />
        </ProjectContext.Provider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );

  return { select };
}

/** The sites have arrived: the table and the site dropdown are filled. */
async function sitesLoaded(): Promise<void> {
  await screen.findByText("PLANT-A");
}

/** Open the project row and wait for the detail panel to hold the project, not "Loading…". */
async function openProject(): Promise<void> {
  const code = await screen.findByText("PRJ-001");
  const row = code.closest("tr");
  if (row === null) {
    throw new Error("no project row");
  }
  fireEvent.click(within(row).getByRole("button", { name: "Open" }));
  await screen.findByRole("heading", { name: /PRJ-001/ });
}

describe("ProjectsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listSitesMock.mockResolvedValue([SITE, CLOSED_SITE]);
    listProjectsMock.mockResolvedValue([PROJECT]);
    getProjectMock.mockResolvedValue(detail());
  });
  afterEach(cleanup);

  it("shows the sites and the projects of the organization", async () => {
    renderPage();
    await sitesLoaded();

    const sites = screen.getByRole("region", { name: "Sites" });
    expect(within(sites).getByRole("row", { name: /PLANT-A/ })).toHaveTextContent("In use");
    expect(within(sites).getByRole("row", { name: /PLANT-B/ })).toHaveTextContent("Inactive");

    const projects = screen.getByRole("region", { name: "Projects" });
    const row = within(projects).getByRole("row", { name: /PRJ-001/ });
    expect(row).toHaveTextContent("Pump House");
    expect(row).toHaveTextContent("Northern Mills");
    expect(row).toHaveTextContent("IN");
    expect(row).toHaveTextContent("Active");
    expect(listSitesMock).toHaveBeenCalledWith(true, expect.anything());
  });

  it("adds a site and reads the list again", async () => {
    createSiteMock.mockResolvedValue({ ...SITE, code: "PLANT-C", name: "Plant C" });
    renderPage();
    await sitesLoaded();
    const form = await screen.findByRole("form", { name: "Add a site" });

    fireEvent.change(within(form).getByLabelText("Code"), { target: { value: " plant-c " } });
    fireEvent.change(within(form).getByLabelText("Name"), { target: { value: "Plant C" } });
    fireEvent.change(within(form).getByLabelText("Location"), { target: { value: "  " } });
    fireEvent.submit(form);

    await waitFor(() =>
      expect(createSiteMock).toHaveBeenCalledWith({
        code: "plant-c",
        name: "Plant C",
        location: null,
      }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Site PLANT-C was created.");
    await waitFor(() => expect(listSitesMock).toHaveBeenCalledTimes(2));
  });

  it("adds a project with its site, profile and first revision label", async () => {
    createProjectMock.mockResolvedValue(detail());
    renderPage();
    await sitesLoaded();
    const form = await screen.findByRole("form", { name: "Add a project" });

    fireEvent.change(within(form).getByLabelText("Site"), { target: { value: SITE_ID } });
    fireEvent.change(within(form).getByLabelText("Code"), { target: { value: "PRJ-002" } });
    fireEvent.change(within(form).getByLabelText("Name"), { target: { value: "Workshop" } });
    fireEvent.change(within(form).getByLabelText("Jurisdiction profile"), {
      target: { value: "IEC" },
    });
    fireEvent.change(within(form).getByLabelText("Client"), { target: { value: "Acme" } });
    fireEvent.submit(form);

    await waitFor(() =>
      expect(createProjectMock).toHaveBeenCalledWith({
        site_id: SITE_ID,
        code: "PRJ-002",
        name: "Workshop",
        jurisdiction_profile: "IEC",
        client_name: "Acme",
        description: null,
        first_revision_label: "Rev 1",
      }),
    );
    await waitFor(() => expect(listProjectsMock).toHaveBeenCalledTimes(2));
  });

  it("offers only the sites that are in use when adding a project", async () => {
    renderPage();
    await sitesLoaded();
    const form = await screen.findByRole("form", { name: "Add a project" });

    const options = [...(within(form).getByLabelText("Site") as HTMLSelectElement).options];

    expect(options.map((option) => option.textContent)).toEqual([
      "Choose a site",
      "PLANT-A — Plant A",
    ]);
  });

  it("shows the server's own refusal next to the form that caused it", async () => {
    createProjectMock.mockRejectedValue(
      new ApiError("A project with this code already exists.", 409),
    );
    renderPage();
    await sitesLoaded();
    const form = await screen.findByRole("form", { name: "Add a project" });

    fireEvent.change(within(form).getByLabelText("Site"), { target: { value: SITE_ID } });
    fireEvent.change(within(form).getByLabelText("Code"), { target: { value: "PRJ-001" } });
    fireEvent.change(within(form).getByLabelText("Name"), { target: { value: "Pump House" } });
    fireEvent.submit(form);

    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "A project with this code already exists.",
    );
  });

  it("opens a project and lists its revisions newest first", async () => {
    renderPage();

    await openProject();

    const panel = screen.getByRole("region", { name: "Project detail" });
    const rows = within(panel).getAllByRole("row").slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining("Rev 2"),
      expect.stringContaining("Rev 1"),
    ]);
    expect(rows[0]).toHaveTextContent("Open");
    expect(rows[1]).toHaveTextContent("Superseded");
    expect(within(panel).getByText(/Site PLANT-A — Plant A/)).toBeInTheDocument();
  });

  it("works in the open revision of the project when asked to", async () => {
    const { select } = renderPage();
    await openProject();

    fireEvent.click(screen.getByRole("button", { name: "Use in studies" }));

    expect(select).toHaveBeenCalledWith(PROJECT_ID, REVISION_2);
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Studies are now saved in PRJ-001.",
    );
  });

  it("cannot work in a project that has no open revision", async () => {
    getProjectMock.mockResolvedValue(
      detail({ revisions: [revision(REVISION_1, 1, "ISSUED")], open_revision_id: null }),
    );
    renderPage();
    await openProject();

    expect(screen.getByRole("button", { name: "Use in studies" })).toBeDisabled();
    expect(
      screen.getByText(/No open revision: new studies are not linked to this project/),
    ).toBeInTheDocument();
  });

  it("opens the next revision, issues one and archives the project", async () => {
    createRevisionMock.mockResolvedValue(revision(REVISION_2, 2, "OPEN"));
    issueRevisionMock.mockResolvedValue(revision(REVISION_2, 2, "ISSUED"));
    archiveProjectMock.mockResolvedValue({ ...PROJECT, status: "ARCHIVED" });
    renderPage();
    await openProject();

    fireEvent.click(screen.getByRole("button", { name: "New revision" }));
    const form = screen.getByRole("form", { name: "New revision" });
    fireEvent.change(within(form).getByLabelText("Label"), { target: { value: " Rev 3 " } });
    fireEvent.change(within(form).getByLabelText("Notes"), { target: { value: "after review" } });
    fireEvent.submit(form);
    await waitFor(() =>
      expect(createRevisionMock).toHaveBeenCalledWith(PROJECT_ID, {
        label: "Rev 3",
        notes: "after review",
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Issue revision" }));
    await waitFor(() => expect(issueRevisionMock).toHaveBeenCalledWith(PROJECT_ID, REVISION_2));

    fireEvent.click(screen.getByRole("button", { name: "Archive project" }));
    await waitFor(() => expect(archiveProjectMock).toHaveBeenCalledWith(PROJECT_ID));
  });

  it("changes the name, the client and the description of a project", async () => {
    updateProjectMock.mockResolvedValue({ ...PROJECT, name: "Pump House B" });
    renderPage();
    await openProject();
    const form = screen.getByRole("form", { name: "Edit project" });

    fireEvent.change(within(form).getByLabelText("Name"), { target: { value: "Pump House B" } });
    fireEvent.change(within(form).getByLabelText("Client"), { target: { value: "" } });
    fireEvent.submit(form);

    await waitFor(() =>
      expect(updateProjectMock).toHaveBeenCalledWith(PROJECT_ID, {
        name: "Pump House B",
        client_name: null,
        description: null,
      }),
    );
  });

  it("switches a site off once the question is answered", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    updateSiteMock.mockResolvedValue({ ...SITE, is_active: false });
    renderPage();
    await sitesLoaded();
    const sites = screen.getByRole("region", { name: "Sites" });

    const row = within(sites).getByRole("row", { name: /PLANT-A/ });
    fireEvent.click(within(row).getByRole("button", { name: "Switch off" }));

    expect(confirmSpy).toHaveBeenCalledWith(
      "Switch off site PLANT-A? It will take no new projects. Existing projects stay unchanged.",
    );
    await waitFor(() => expect(updateSiteMock).toHaveBeenCalledWith(SITE_ID, { is_active: false }));
    confirmSpy.mockRestore();
  });

  it("changes nothing when the question is answered no", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderPage();
    await sitesLoaded();
    const sites = screen.getByRole("region", { name: "Sites" });

    const row = within(sites).getByRole("row", { name: /PLANT-A/ });
    fireEvent.click(within(row).getByRole("button", { name: "Switch off" }));

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(updateSiteMock).not.toHaveBeenCalled();
    // No request means nothing to report either way.
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it("switches a site back on with one click", async () => {
    const confirmSpy = vi.spyOn(window, "confirm");
    listSitesMock.mockResolvedValue([{ ...SITE, is_active: false }]);
    updateSiteMock.mockResolvedValue({ ...SITE, is_active: true });
    renderPage();
    await sitesLoaded();
    const sites = screen.getByRole("region", { name: "Sites" });

    const row = within(sites).getByRole("row", { name: /PLANT-A/ });
    fireEvent.click(within(row).getByRole("button", { name: "Switch on" }));

    // Switching on takes nothing away, so it asks nothing.
    expect(confirmSpy).not.toHaveBeenCalled();
    await waitFor(() => expect(updateSiteMock).toHaveBeenCalledWith(SITE_ID, { is_active: true }));
    confirmSpy.mockRestore();
  });

  it("shows a viewer everything and lets them write nothing", async () => {
    renderPage("VIEWER");
    await openProject();

    expect(screen.queryByRole("form", { name: "Add a site" })).not.toBeInTheDocument();
    expect(screen.queryByRole("form", { name: "Add a project" })).not.toBeInTheDocument();
    expect(screen.queryByRole("form", { name: "Edit project" })).not.toBeInTheDocument();
    for (const name of ["Switch off", "New revision", "Issue revision", "Archive project"]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
    // Reading the project and choosing it for the study pages writes nothing.
    expect(screen.getByRole("button", { name: "Use in studies" })).toBeEnabled();
    expect(screen.getByRole("row", { name: /Rev 2/ })).toBeInTheDocument();
  });

  it("lets an engineer keep the projects but not issue or archive", async () => {
    renderPage("ENGINEER");
    await openProject();

    expect(screen.getByRole("form", { name: "Add a site" })).toBeInTheDocument();
    expect(screen.getByRole("form", { name: "Add a project" })).toBeInTheDocument();
    expect(screen.getByRole("form", { name: "Edit project" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New revision" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Issue revision" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Archive project" })).not.toBeInTheDocument();
  });

  it("says so when the lists cannot be loaded", async () => {
    listSitesMock.mockRejectedValue(new ApiError("The sites could not be loaded", 500));
    listProjectsMock.mockRejectedValue(new ApiError("The projects could not be loaded", 500));
    renderPage();

    const alerts = await screen.findAllByRole("alert");
    expect(alerts.map((alert) => alert.textContent)).toEqual([
      "The sites could not be loaded",
      "The projects could not be loaded",
    ]);
  });
});
