// @vitest-environment jsdom
import { cleanup, render, screen, within } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Session } from "../services/auth";
import { AppShell } from "./AppShell";
import { AuthContext, type AuthContextValue } from "./authContext";
import { ProjectContext, type ProjectContextValue } from "./projectContext";
import { MODULES } from "./modules";

// The topbar carries the project selector, which reads the project list through react-query;
// the shell tests are about the shell, so they run with no project chosen.
vi.mock("../services/projects", () => ({ getProject: vi.fn(), listProjects: vi.fn(() => []) }));

const NO_PROJECT: ProjectContextValue = {
  state: { status: "none" },
  select: vi.fn(),
  clear: vi.fn(),
  activeRevisionId: () => null,
};

const SESSION: Session = {
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
};

// The shell is only ever rendered behind RequireAuth, so every test runs signed in.
const AUTH: AuthContextValue = {
  state: { status: "signed-in", session: SESSION },
  signIn: () => Promise.reject(new Error("not used")),
  signOut: () => Promise.resolve(),
  refresh: () => Promise.resolve(),
};

function renderShell(initialEntry: string) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <AppShell />,
        children: [
          { index: true, element: <p>home page</p> },
          { path: "cable-sizing", element: <p>cable page</p> },
          { path: "fault-study", element: <p>fault page</p> },
        ],
      },
    ],
    { initialEntries: [initialEntry] },
  );
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={AUTH}>
        <ProjectContext.Provider value={NO_PROJECT}>
          <RouterProvider router={router} />
        </ProjectContext.Provider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

describe("AppShell", () => {
  afterEach(cleanup);

  it("lists every registry module in the sidebar with its status", () => {
    renderShell("/");
    const nav = screen.getByRole("navigation", { name: "Primary" });
    for (const module of MODULES) {
      const item = nav.querySelector(`[data-module-code="${module.code}"]`);
      expect(item).not.toBeNull();
      expect(item?.querySelector("[data-module-status]")).not.toBeNull();
    }
    expect(nav.querySelector('[data-module-code="EOS-06"] [data-module-status="Live"]')).not.toBeNull();
    expect(
      nav.querySelector('[data-module-code="EOS-05"] [data-module-status="Planned"]'),
    ).not.toBeNull();
  });

  it("links only modules that have a working page", () => {
    renderShell("/");
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getByRole("link", { name: /Cable sizing/ }).getAttribute("href")).toBe(
      "/cable-sizing",
    );
    expect(within(nav).getByRole("link", { name: /Short-circuit study/ }).getAttribute("href")).toBe(
      "/fault-study",
    );
    expect(within(nav).queryByRole("link", { name: /Earthing/ })).toBeNull();
    expect(nav.querySelector('[data-module-code="EOS-08"] [aria-disabled="true"]')).not.toBeNull();
  });

  it("marks the active route and renders the routed page inside the shell", () => {
    renderShell("/cable-sizing");
    expect(screen.getByRole("link", { name: /Cable sizing/ }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getByRole("link", { name: /Home/ }).getAttribute("aria-current")).toBeNull();
    expect(screen.getByText("cable page")).not.toBeNull();
  });

  it("shows no back control in the topbar on Home", () => {
    renderShell("/");
    const header = document.querySelector('header[aria-label="Product"]');
    expect(header).not.toBeNull();
    expect(header?.querySelector("[data-shell-back]")).toBeNull();
  });

  it("puts the back control first in the topbar on a module page (A10)", () => {
    renderShell("/cable-sizing");
    const header = document.querySelector('header[aria-label="Product"]');
    expect(header?.firstElementChild?.hasAttribute("data-shell-back")).toBe(true);
    expect(screen.getByRole("button", { name: "Back" })).not.toBeNull();
  });

  it("shows the signed-in user with the account actions last in the topbar", () => {
    renderShell("/cable-sizing");
    const header = document.querySelector('header[aria-label="Product"]');
    const user = header?.lastElementChild;
    expect(user?.hasAttribute("data-shell-user")).toBe(true);
    expect(user?.textContent).toContain("Test Owner");
    expect(user?.textContent).toContain("Owner · KES");
    expect(screen.getByRole("link", { name: "Change password" })).not.toBeNull();
    expect(screen.getByRole("button", { name: "Sign out" })).not.toBeNull();
  });

  it("names the signed-in organization once and no fixed company beside it", () => {
    renderShell("/");
    const header = document.querySelector('header[aria-label="Product"]');
    expect(header?.textContent).not.toContain("Kamra Engineering Solutions");
    expect(header?.querySelectorAll(":scope > span")).toHaveLength(1);
  });

  it("states the engineering basis in the footer", () => {
    renderShell("/");
    const footer = document.querySelector('footer[aria-label="Engineering basis"]');
    expect(footer).not.toBeNull();
    expect(footer?.textContent).toContain("not a statutory compliance certification");
    expect(footer?.textContent).toContain("no manufacturer is named");
  });
});
