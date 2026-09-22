import { z } from "zod";

import { jurisdictionProfileSchema, type JurisdictionProfile } from "./cableContract";
import { ApiError, describeApiError, requestJson } from "./http";

// Sites, projects and project revisions of the signed-in organization (EOS-01 b).
//
// A project states the jurisdiction profile its studies are designed under, and carries
// numbered revisions; calculation runs are attached to the one revision that is still OPEN.
// The organization is never sent: the server takes it from the session and answers "not
// found" for anything belonging to another organization.

export const projectStatusSchema = z.enum(["ACTIVE", "ARCHIVED"]);
export const projectRevisionStatusSchema = z.enum(["OPEN", "ISSUED", "SUPERSEDED"]);

export const siteSchema = z
  .object({
    id: z.string().uuid(),
    code: z.string(),
    name: z.string(),
    location: z.string().nullable(),
    is_active: z.boolean(),
    created_at: z.string(),
  })
  .strict();

export const projectRevisionSchema = z
  .object({
    id: z.string().uuid(),
    project_id: z.string().uuid(),
    revision_number: z.number().int().positive(),
    label: z.string(),
    status: projectRevisionStatusSchema,
    created_by: z.string().nullable(),
    issued_by: z.string().nullable(),
    issued_at: z.string().nullable(),
    notes: z.string().nullable(),
    created_at: z.string(),
  })
  .strict();

const projectFields = {
  id: z.string().uuid(),
  site_id: z.string().uuid(),
  code: z.string(),
  name: z.string(),
  client_name: z.string().nullable(),
  jurisdiction_profile: jurisdictionProfileSchema,
  status: projectStatusSchema,
  description: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
};

export const projectSchema = z.object(projectFields).strict();

/** One project with its revisions, newest first, and the revision that takes new runs. */
export const projectDetailSchema = z
  .object({
    ...projectFields,
    revisions: z.array(projectRevisionSchema),
    open_revision_id: z.string().uuid().nullable(),
  })
  .strict();

/** The project and revision a calculation run belongs to, as the run responses carry it. */
export const projectRevisionSummarySchema = z
  .object({
    revision_id: z.string().uuid(),
    revision_number: z.number().int().positive(),
    revision_label: z.string(),
    project_id: z.string().uuid(),
    project_code: z.string(),
    project_name: z.string(),
  })
  .strict();

const siteListSchema = z.object({ items: z.array(siteSchema) }).strict();
const projectListSchema = z.object({ items: z.array(projectSchema) }).strict();
const revisionListSchema = z.object({ items: z.array(projectRevisionSchema) }).strict();

export type ProjectStatus = z.infer<typeof projectStatusSchema>;
export type ProjectRevisionStatus = z.infer<typeof projectRevisionStatusSchema>;
export type Site = z.infer<typeof siteSchema>;
export type Project = z.infer<typeof projectSchema>;
export type ProjectDetail = z.infer<typeof projectDetailSchema>;
export type ProjectRevision = z.infer<typeof projectRevisionSchema>;
export type ProjectRevisionSummary = z.infer<typeof projectRevisionSummarySchema>;

export { jurisdictionProfileSchema, type JurisdictionProfile };

export type NewSite = {
  code: string;
  name: string;
  location?: string | null;
};

/** Only the fields that are given are changed; the code of a site never changes. */
export type SiteChange = {
  name?: string;
  location?: string | null;
  is_active?: boolean;
};

export type NewProject = {
  site_id: string;
  code: string;
  name: string;
  jurisdiction_profile: JurisdictionProfile;
  client_name?: string | null;
  description?: string | null;
  first_revision_label?: string;
};

/** Only the fields that are given are changed; code, site and profile stay as they are. */
export type ProjectChange = {
  name?: string;
  client_name?: string | null;
  description?: string | null;
};

export type NewRevision = {
  label: string;
  notes?: string | null;
};

const SITES = "/api/v1/sites";
const PROJECTS = "/api/v1/projects";
const UNEXPECTED = "Unexpected response from the KES Electrical OS projects API.";

function refusal(data: unknown, status: number, fallback: string): ApiError {
  return new ApiError(describeApiError(data, status, fallback), status);
}

function parse<T>(schema: z.ZodType<T>, data: unknown): T {
  const parsed = schema.safeParse(data);

  if (!parsed.success) {
    throw new Error(UNEXPECTED);
  }

  return parsed.data;
}

function projectPath(projectId: string, suffix = ""): string {
  return `${PROJECTS}/${encodeURIComponent(projectId)}${suffix}`;
}

// -- sites ---------------------------------------------------------------------------------

/** The sites of the organization; inactive ones only when they are asked for. */
export async function listSites(includeInactive = false, signal?: AbortSignal): Promise<Site[]> {
  const url = includeInactive ? `${SITES}?include_inactive=true` : SITES;
  const response = await requestJson(url, { method: "GET", signal });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The site list could not be loaded");
  }

  return parse(siteListSchema, response.data).items;
}

/** Add a site; its code is unique within the organization. */
export async function createSite(site: NewSite): Promise<Site> {
  const response = await requestJson(SITES, { method: "POST", body: site });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The site was not created");
  }

  return parse(siteSchema, response.data);
}

/** Rename a site, correct its location, or take it out of use. */
export async function updateSite(siteId: string, change: SiteChange): Promise<Site> {
  const response = await requestJson(`${SITES}/${encodeURIComponent(siteId)}`, {
    method: "PATCH",
    body: change,
  });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The site was not changed");
  }

  return parse(siteSchema, response.data);
}

// -- projects ------------------------------------------------------------------------------

/** The projects of the organization, filtered by status when one is given. */
export async function listProjects(
  status?: ProjectStatus,
  signal?: AbortSignal,
): Promise<Project[]> {
  const url = status ? `${PROJECTS}?status=${status}` : PROJECTS;
  const response = await requestJson(url, { method: "GET", signal });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The project list could not be loaded");
  }

  return parse(projectListSchema, response.data).items;
}

/** Create a project at one of the organization's sites; the server opens its revision 1. */
export async function createProject(project: NewProject): Promise<ProjectDetail> {
  const response = await requestJson(PROJECTS, { method: "POST", body: project });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The project was not created");
  }

  return parse(projectDetailSchema, response.data);
}

/** One project with its revisions and the revision that still takes runs. */
export async function getProject(projectId: string, signal?: AbortSignal): Promise<ProjectDetail> {
  const response = await requestJson(projectPath(projectId), { method: "GET", signal });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The project could not be loaded");
  }

  return parse(projectDetailSchema, response.data);
}

/** Correct the name, the client or the description; an archived project is read-only. */
export async function updateProject(projectId: string, change: ProjectChange): Promise<Project> {
  const response = await requestJson(projectPath(projectId), {
    method: "PATCH",
    body: change,
  });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The project was not changed");
  }

  return parse(projectSchema, response.data);
}

/** Close a project for good: no change, no new revision and no new run after this. */
export async function archiveProject(projectId: string): Promise<Project> {
  const response = await requestJson(projectPath(projectId, "/archive"), { method: "POST" });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The project was not archived");
  }

  return parse(projectSchema, response.data);
}

// -- revisions -----------------------------------------------------------------------------

/** All revisions of a project, newest first. */
export async function listRevisions(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectRevision[]> {
  const response = await requestJson(projectPath(projectId, "/revisions"), {
    method: "GET",
    signal,
  });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The revisions could not be loaded");
  }

  return parse(revisionListSchema, response.data).items;
}

/** Open the next revision; the one that was open becomes superseded. */
export async function createRevision(
  projectId: string,
  revision: NewRevision,
): Promise<ProjectRevision> {
  const response = await requestJson(projectPath(projectId, "/revisions"), {
    method: "POST",
    body: revision,
  });

  if (!response.ok) {
    throw refusal(response.data, response.status, "The revision was not created");
  }

  return parse(projectRevisionSchema, response.data);
}

/** Freeze the open revision as the issued record; owners only. */
export async function issueRevision(
  projectId: string,
  revisionId: string,
): Promise<ProjectRevision> {
  const response = await requestJson(
    projectPath(projectId, `/revisions/${encodeURIComponent(revisionId)}/issue`),
    { method: "POST" },
  );

  if (!response.ok) {
    throw refusal(response.data, response.status, "The revision was not issued");
  }

  return parse(projectRevisionSchema, response.data);
}
