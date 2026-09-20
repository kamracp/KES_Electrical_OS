// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getSession, type Session } from "../services/auth";
import { routes } from "./routes";

// The real route table with the real provider, guards and shell; only the session request
// and the three module pages (which would call the API) are replaced.
vi.mock("../services/auth", () => ({
  getSession: vi.fn(),
  signIn: vi.fn(),
  signOut: vi.fn(),
}));
vi.mock("../App", () => ({ App: () => <p>home page</p> }));
vi.mock("../pages/CableSizingPage", () => ({ CableSizingPage: () => <p>cable page</p> }));
vi.mock("../pages/FaultStudyPage", () => ({ FaultStudyPage: () => <p>fault page</p> }));
vi.mock("../pages/UsersPage", () => ({ UsersPage: () => <p>users page</p> }));

function sessionOf(mustChangePassword: boolean): Session {
  return {
    user: {
      id: "7b0c0a3e-5d0e-4a53-9c58-0d1f6f2f7a11",
      email: "owner@example.com",
      full_name: "Test Owner",
      must_change_password: mustChangePassword,
    },
    organization: { id: "c1b7f1de-32a4-4c0b-8a4e-3f1f2a9d5b22", code: "KES", name: "KES" },
    role: "OWNER",
    session_expires_at: "2026-09-27T10:00:00Z",
    idle_timeout_minutes: 720,
  };
}

function renderApp(initialEntry: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [initialEntry] });
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

describe("application routes", () => {
  beforeEach(() => {
    vi.mocked(getSession).mockReset();
  });
  afterEach(cleanup);

  it.each(["/", "/cable-sizing", "/fault-study", "/users"])(
    "shows the sign-in page instead of %s to a signed-out visitor",
    async (path) => {
      vi.mocked(getSession).mockResolvedValue(null);
      const router = renderApp(path);

      expect(await screen.findByRole("heading", { name: "Sign in" })).not.toBeNull();
      expect(router.state.location.pathname).toBe("/login");
      expect(router.state.location.state).toEqual({ from: path });
      expect(screen.queryByRole("navigation", { name: "Primary" })).toBeNull();
    },
  );

  it("shows no page and no shell while the session is being checked", () => {
    vi.mocked(getSession).mockReturnValue(new Promise(() => {}));
    renderApp("/cable-sizing");

    expect(screen.getByRole("status")).not.toBeNull();
    expect(screen.queryByText("cable page")).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Primary" })).toBeNull();
  });

  it("shows the module page inside the shell to a signed-in user", async () => {
    vi.mocked(getSession).mockResolvedValue(sessionOf(false));
    renderApp("/cable-sizing");

    expect(await screen.findByText("cable page")).not.toBeNull();
    expect(screen.getByRole("navigation", { name: "Primary" })).not.toBeNull();
  });

  it("shows the users page inside the shell to a signed-in user", async () => {
    vi.mocked(getSession).mockResolvedValue(sessionOf(false));
    renderApp("/users");

    expect(await screen.findByText("users page")).not.toBeNull();
    expect(screen.getByRole("navigation", { name: "Primary" })).not.toBeNull();
  });

  it("sends a signed-in user from the sign-in page to Home", async () => {
    vi.mocked(getSession).mockResolvedValue(sessionOf(false));
    const router = renderApp("/login");

    expect(await screen.findByText("home page")).not.toBeNull();
    expect(router.state.location.pathname).toBe("/");
  });

  it("holds a user with a password change due on the change-password page", async () => {
    vi.mocked(getSession).mockResolvedValue(sessionOf(true));
    const router = renderApp("/fault-study");

    expect(await screen.findByRole("heading", { name: "Change your password" })).not.toBeNull();
    await waitFor(() => expect(router.state.location.pathname).toBe("/change-password"));
    expect(screen.queryByText("fault page")).toBeNull();
  });
});
