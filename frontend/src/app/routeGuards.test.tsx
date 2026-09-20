// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Session } from "../services/auth";
import { AuthContext, type AuthContextValue, type AuthState } from "./authContext";
import { RequireAuth, SignedOutOnly } from "./routeGuards";

function sessionOf(mustChangePassword: boolean): Session {
  return {
    user: {
      id: "7b0c0a3e-5d0e-4a53-9c58-0d1f6f2f7a11",
      email: "engineer@example.com",
      full_name: "Test Engineer",
      must_change_password: mustChangePassword,
    },
    organization: { id: "c1b7f1de-32a4-4c0b-8a4e-3f1f2a9d5b22", code: "KES", name: "KES" },
    role: "ENGINEER",
    session_expires_at: "2026-09-27T10:00:00Z",
    idle_timeout_minutes: 720,
  };
}

const SIGNED_IN: AuthState = { status: "signed-in", session: sessionOf(false) };
const PASSWORD_DUE: AuthState = { status: "signed-in", session: sessionOf(true) };

function LoginProbe() {
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "none";
  return <p>login page, from: {from}</p>;
}

type Entry = string | { pathname: string; state: unknown };

function renderRoutes(state: AuthState, entry: Entry, refresh = vi.fn(async () => {})) {
  const value: AuthContextValue = {
    state,
    signIn: vi.fn(),
    signOut: vi.fn(),
    refresh,
  };
  const router = createMemoryRouter(
    [
      {
        path: "/login",
        element: (
          <SignedOutOnly>
            <LoginProbe />
          </SignedOutOnly>
        ),
      },
      {
        path: "/change-password",
        element: (
          <RequireAuth allowPasswordChangePending>
            <p>change password page</p>
          </RequireAuth>
        ),
      },
      {
        path: "/",
        element: (
          <RequireAuth>
            <p>home page</p>
          </RequireAuth>
        ),
      },
      {
        path: "/cable-sizing",
        element: (
          <RequireAuth>
            <p>cable page</p>
          </RequireAuth>
        ),
      },
    ],
    { initialEntries: [entry] },
  );
  render(
    <AuthContext.Provider value={value}>
      <RouterProvider router={router} />
    </AuthContext.Provider>,
  );
  return { router, refresh };
}

describe("RequireAuth", () => {
  afterEach(cleanup);

  it("shows nothing but a status line while the session is being checked", () => {
    renderRoutes({ status: "loading" }, "/cable-sizing");

    expect(screen.getByRole("status").textContent).toContain("Checking your session");
    expect(screen.queryByText("cable page")).toBeNull();
  });

  it("sends a signed-out visitor to the sign-in page and remembers the target", () => {
    const { router } = renderRoutes({ status: "signed-out" }, "/cable-sizing?run=abc");

    expect(router.state.location.pathname).toBe("/login");
    expect(screen.getByText("login page, from: /cable-sizing?run=abc")).not.toBeNull();
    expect(screen.queryByText("cable page")).toBeNull();
  });

  it("shows the page to a signed-in user", () => {
    renderRoutes(SIGNED_IN, "/cable-sizing");

    expect(screen.getByText("cable page")).not.toBeNull();
  });

  it("sends a user whose password change is due to the change-password page", () => {
    const { router } = renderRoutes(PASSWORD_DUE, "/cable-sizing");

    expect(router.state.location.pathname).toBe("/change-password");
    expect(screen.getByText("change password page")).not.toBeNull();
    expect(screen.queryByText("cable page")).toBeNull();
  });

  it("keeps the change-password page open for a user who has nothing due", () => {
    renderRoutes(SIGNED_IN, "/change-password");

    expect(screen.getByText("change password page")).not.toBeNull();
  });

  it("sends a signed-out visitor away from the change-password page", () => {
    const { router } = renderRoutes({ status: "signed-out" }, "/change-password");

    expect(router.state.location.pathname).toBe("/login");
  });

  it("shows the failure and no page when the session check failed, and can retry", () => {
    const { refresh } = renderRoutes(
      { status: "error", message: "The session could not be checked (HTTP 502)." },
      "/cable-sizing",
    );

    expect(screen.getByRole("alert").textContent).toContain("HTTP 502");
    expect(screen.queryByText("cable page")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(refresh).toHaveBeenCalledTimes(1);
  });
});

describe("SignedOutOnly", () => {
  afterEach(cleanup);

  it("shows the sign-in page to a signed-out visitor", () => {
    renderRoutes({ status: "signed-out" }, "/login");

    expect(screen.getByText("login page, from: none")).not.toBeNull();
  });

  it("holds the sign-in page back while the session is being checked", () => {
    renderRoutes({ status: "loading" }, "/login");

    expect(screen.getByRole("status")).not.toBeNull();
    expect(screen.queryByText(/login page/)).toBeNull();
  });

  it("sends a signed-in user on to the page they came for", () => {
    const { router } = renderRoutes(SIGNED_IN, {
      pathname: "/login",
      state: { from: "/cable-sizing" },
    });

    expect(router.state.location.pathname).toBe("/cable-sizing");
    expect(screen.getByText("cable page")).not.toBeNull();
  });

  it("sends a signed-in user home when no target was remembered", () => {
    const { router } = renderRoutes(SIGNED_IN, "/login");

    expect(router.state.location.pathname).toBe("/");
  });

  it.each([
    ["an absolute address", "https://example.com/steal"],
    ["a protocol-relative address", "//example.com/steal"],
    ["a backslash address", "/\\example.com"],
    ["the sign-in page itself", "/login"],
    ["something that is not text", 42],
  ])("ignores %s as the place to return to", (_label, from) => {
    const { router } = renderRoutes(SIGNED_IN, { pathname: "/login", state: { from } });

    expect(router.state.location.pathname).toBe("/");
    expect(screen.getByText("home page")).not.toBeNull();
  });

  it("sends a signed-in user whose password change is due to the change-password page", () => {
    const { router } = renderRoutes(PASSWORD_DUE, {
      pathname: "/login",
      state: { from: "/cable-sizing" },
    });

    expect(router.state.location.pathname).toBe("/change-password");
  });
});
