// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ProjectContext,
  type ProjectContextValue,
  type ProjectState,
} from "../app/projectContext";
import type { Project, ProjectRevision } from "../services/projects";
import { StudyProjectLine } from "./StudyProjectLine";

const PROJECT: Project = {
  id: "2a7d5c31-9b0e-4a21-8f6c-7d8e9f0a1b2c",
  site_id: "6f1c9f1e-6a2b-4f5c-9b3d-1e2f3a4b5c6d",
  code: "PRJ-001",
  name: "Pump House",
  client_name: "Northern Mills",
  jurisdiction_profile: "IN",
  status: "ACTIVE",
  description: null,
  created_at: "2026-09-22T09:00:00Z",
  updated_at: "2026-09-22T09:00:00Z",
};

function revision(status: ProjectRevision["status"]): ProjectRevision {
  return {
    id: "4b8e6d42-1c3f-4b5a-9e7d-8f9a0b1c2d3e",
    project_id: PROJECT.id,
    revision_number: 2,
    label: "Rev 2",
    status,
    created_by: null,
    issued_by: null,
    issued_at: null,
    notes: null,
    created_at: "2026-09-22T09:00:00Z",
  };
}

function renderLine(state: ProjectState) {
  const value: ProjectContextValue = {
    state,
    select: vi.fn(),
    clear: vi.fn(),
    activeRevisionId: () => null,
  };

  render(
    <ProjectContext.Provider value={value}>
      <MemoryRouter>
        <StudyProjectLine />
      </MemoryRouter>
    </ProjectContext.Provider>,
  );
}

describe("StudyProjectLine", () => {
  afterEach(cleanup);

  it("names the project and the revision the run will be saved in", () => {
    renderLine({ status: "selected", project: PROJECT, revision: revision("OPEN") });

    expect(screen.getByText(/Project PRJ-001 — Pump House · Rev 2 \(Open\)/)).toBeInTheDocument();
    expect(screen.queryByText(/will not be linked/)).not.toBeInTheDocument();
  });

  it("says plainly when the run belongs to no project", () => {
    renderLine({ status: "none" });

    expect(screen.getByText(/No project — this run will be unassigned/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Projects" })).toHaveAttribute("href", "/projects");
  });

  it("warns that a project without an open revision takes no run", () => {
    renderLine({ status: "read-only", project: PROJECT, revision: revision("ISSUED") });

    expect(screen.getByText(/Project PRJ-001 — Pump House · Rev 2 \(Issued\)/)).toBeInTheDocument();
    expect(
      screen.getByText(/No open revision — this run will not be linked to this project/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Projects" })).toBeInTheDocument();
  });
});
