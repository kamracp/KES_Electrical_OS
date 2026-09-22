import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  archiveProject,
  createProject,
  createRevision,
  createSite,
  getProject,
  issueRevision,
  jurisdictionProfileSchema,
  listProjects,
  listRevisions,
  listSites,
  projectDetailSchema,
  projectRevisionStatusSchema,
  projectRevisionSummarySchema,
  projectStatusSchema,
  updateProject,
  updateSite,
  type Project,
  type ProjectRevision,
  type Site,
} from "./projects";

// Payloads as backend/app/schemas/project.py serialises them.
const SITE: Site = {
  id: "6f1c9f1e-6a2b-4f5c-9b3d-1e2f3a4b5c6d",
  code: "PLANT-A",
  name: "Plant A",
  location: "Ludhiana",
  is_active: true,
  created_at: "2026-09-22T09:00:00Z",
};

const PROJECT: Project = {
  id: "2a7d5c31-9b0e-4a21-8f6c-7d8e9f0a1b2c",
  site_id: SITE.id,
  code: "PRJ-001",
  name: "Pump House",
  client_name: "Northern Mills",
  jurisdiction_profile: "IN",
  status: "ACTIVE",
  description: "Feeder study for the pump house.",
  created_at: "2026-09-22T09:00:00Z",
  updated_at: "2026-09-22T09:00:00Z",
};

const REVISION: ProjectRevision = {
  id: "4b8e6d42-1c3f-4b5a-9e7d-8f9a0b1c2d3e",
  project_id: PROJECT.id,
  revision_number: 1,
  label: "Rev 1",
  status: "OPEN",
  created_by: "Test Owner (owner@example.com)",
  issued_by: null,
  issued_at: null,
  notes: null,
  created_at: "2026-09-22T09:00:00Z",
};

const PROJECT_DETAIL = {
  ...PROJECT,
  revisions: [REVISION],
  open_revision_id: REVISION.id,
};

const fetchMock = vi.fn<typeof fetch>();

function lastRequest(): { url: string; init: RequestInit } {
  const call = fetchMock.mock.calls.at(-1);
  if (call === undefined) {
    throw new Error("fetch was not called");
  }
  return { url: String(call[0]), init: call[1] ?? {} };
}

function sentBody(): unknown {
  return JSON.parse(String(lastRequest().init.body));
}

describe("project contract enums", () => {
  // Verbatim mirror of the backend enums: ProjectStatus and ProjectRevisionStatus in
  // backend/app/models/project.py, JurisdictionProfile in
  // backend/app/domain/electrical/jurisdiction/jurisdiction_models.py.
  it.each<[string, readonly string[], string[]]>([
    ["ProjectStatus", projectStatusSchema.options, ["ACTIVE", "ARCHIVED"]],
    [
      "ProjectRevisionStatus",
      projectRevisionStatusSchema.options,
      ["OPEN", "ISSUED", "SUPERSEDED"],
    ],
    [
      "JurisdictionProfile",
      jurisdictionProfileSchema.options,
      ["IN", "IEC", "US", "UK", "AU_NZ", "EU"],
    ],
  ])("mirrors the backend %s members", (_name, options, expected) => {
    expect([...options]).toEqual(expected);
  });
});

describe("project schemas", () => {
  it("parses a project detail with its revisions and the open revision", () => {
    const parsed = projectDetailSchema.safeParse(PROJECT_DETAIL);

    expect(parsed.error?.issues ?? []).toEqual([]);
    expect(parsed.data?.revisions[0]?.status).toBe("OPEN");
    expect(parsed.data?.open_revision_id).toBe(REVISION.id);
  });

  it("parses the revision summary a run answer carries", () => {
    const summary = {
      revision_id: REVISION.id,
      revision_number: 1,
      revision_label: "Rev 1",
      project_id: PROJECT.id,
      project_code: "PRJ-001",
      project_name: "Pump House",
    };

    expect(projectRevisionSummarySchema.safeParse(summary).success).toBe(true);
  });

  it("rejects a key the backend does not send", () => {
    const parsed = projectDetailSchema.safeParse({ ...PROJECT_DETAIL, organization_id: "x" });

    expect(parsed.success).toBe(false);
    expect(parsed.error?.issues[0]?.code).toBe("unrecognized_keys");
  });
});

describe("projects service", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists the active sites and asks for the inactive ones only when wanted", async () => {
    // A Response body can be read once, so each call needs its own answer.
    fetchMock.mockImplementation(async () => Response.json({ items: [SITE] }));

    await expect(listSites()).resolves.toEqual([SITE]);
    expect(lastRequest().url).toBe("/api/v1/sites");
    expect(lastRequest().init.method).toBe("GET");
    expect(lastRequest().init.credentials).toBe("same-origin");

    await listSites(true);
    expect(lastRequest().url).toBe("/api/v1/sites?include_inactive=true");
  });

  it("creates a site and returns it", async () => {
    fetchMock.mockResolvedValue(Response.json(SITE, { status: 201 }));

    await expect(createSite({ code: "PLANT-A", name: "Plant A" })).resolves.toEqual(SITE);
    expect(lastRequest().url).toBe("/api/v1/sites");
    expect(lastRequest().init.method).toBe("POST");
    expect(sentBody()).toEqual({ code: "PLANT-A", name: "Plant A" });
  });

  it("changes a site with only the fields that are given", async () => {
    fetchMock.mockResolvedValue(Response.json({ ...SITE, is_active: false }));

    await expect(updateSite(SITE.id, { is_active: false })).resolves.toMatchObject({
      is_active: false,
    });
    expect(lastRequest().url).toBe(`/api/v1/sites/${SITE.id}`);
    expect(lastRequest().init.method).toBe("PATCH");
    expect(sentBody()).toEqual({ is_active: false });
  });

  it("lists the projects and filters them by status", async () => {
    fetchMock.mockImplementation(async () => Response.json({ items: [PROJECT] }));

    await expect(listProjects()).resolves.toEqual([PROJECT]);
    expect(lastRequest().url).toBe("/api/v1/projects");

    await listProjects("ARCHIVED");
    expect(lastRequest().url).toBe("/api/v1/projects?status=ARCHIVED");
  });

  it("creates a project and receives it with its first revision", async () => {
    fetchMock.mockResolvedValue(Response.json(PROJECT_DETAIL, { status: 201 }));

    const created = await createProject({
      site_id: SITE.id,
      code: "PRJ-001",
      name: "Pump House",
      jurisdiction_profile: "IN",
    });

    expect(created.open_revision_id).toBe(REVISION.id);
    expect(created.revisions).toHaveLength(1);
    expect(lastRequest().init.method).toBe("POST");
    expect(sentBody()).toMatchObject({ code: "PRJ-001", jurisdiction_profile: "IN" });
  });

  it("loads one project with its revisions", async () => {
    fetchMock.mockResolvedValue(Response.json(PROJECT_DETAIL));

    await expect(getProject(PROJECT.id)).resolves.toEqual(PROJECT_DETAIL);
    expect(lastRequest().url).toBe(`/api/v1/projects/${PROJECT.id}`);
    expect(lastRequest().init.method).toBe("GET");
  });

  it("changes a project and archives it", async () => {
    fetchMock.mockResolvedValue(Response.json({ ...PROJECT, name: "Pump House B" }));
    await expect(updateProject(PROJECT.id, { name: "Pump House B" })).resolves.toMatchObject({
      name: "Pump House B",
    });
    expect(lastRequest().init.method).toBe("PATCH");

    fetchMock.mockResolvedValue(Response.json({ ...PROJECT, status: "ARCHIVED" }));
    await expect(archiveProject(PROJECT.id)).resolves.toMatchObject({ status: "ARCHIVED" });
    expect(lastRequest().url).toBe(`/api/v1/projects/${PROJECT.id}/archive`);
    expect(lastRequest().init.method).toBe("POST");
  });

  it("lists the revisions and opens the next one", async () => {
    fetchMock.mockResolvedValue(Response.json({ items: [REVISION] }));
    await expect(listRevisions(PROJECT.id)).resolves.toEqual([REVISION]);
    expect(lastRequest().url).toBe(`/api/v1/projects/${PROJECT.id}/revisions`);

    const second = { ...REVISION, id: REVISION.project_id, revision_number: 2, label: "Rev 2" };
    fetchMock.mockResolvedValue(Response.json(second, { status: 201 }));
    await expect(createRevision(PROJECT.id, { label: "Rev 2" })).resolves.toMatchObject({
      revision_number: 2,
    });
    expect(sentBody()).toEqual({ label: "Rev 2" });
  });

  it("issues a revision through its project", async () => {
    const issued = {
      ...REVISION,
      status: "ISSUED",
      issued_by: "Test Owner (owner@example.com)",
      issued_at: "2026-09-22T10:00:00Z",
    };
    fetchMock.mockResolvedValue(Response.json(issued));

    await expect(issueRevision(PROJECT.id, REVISION.id)).resolves.toMatchObject({
      status: "ISSUED",
    });
    expect(lastRequest().url).toBe(
      `/api/v1/projects/${PROJECT.id}/revisions/${REVISION.id}/issue`,
    );
    expect(lastRequest().init.method).toBe("POST");
  });

  it("carries the server's message and status when a code is already taken (409)", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "A project with this code already exists." }, { status: 409 }),
    );

    await expect(createProject({ site_id: SITE.id, code: "PRJ-001", name: "x", jurisdiction_profile: "IN" })).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
      message: "A project with this code already exists.",
    });
  });

  it("carries the server's message and status when the project is gone (404)", async () => {
    fetchMock.mockResolvedValue(Response.json({ detail: "Project not found." }, { status: 404 }));

    await expect(getProject(PROJECT.id)).rejects.toMatchObject({
      status: 404,
      message: "Project not found.",
    });
  });

  it("says so plainly when a role is missing (403) or the session is gone (401)", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "This action needs the role OWNER." }, { status: 403 }),
    );
    await expect(archiveProject(PROJECT.id)).rejects.toMatchObject({
      status: 403,
      message: "This action needs the role OWNER.",
    });

    fetchMock.mockResolvedValue(new Response(null, { status: 401 }));
    await expect(listProjects()).rejects.toMatchObject({ status: 401 });
  });

  it("refuses an answer with a field it does not know", async () => {
    fetchMock.mockResolvedValue(Response.json({ items: [{ ...PROJECT, secret: "x" }] }));

    await expect(listProjects()).rejects.toThrow("Unexpected response");
  });
});
