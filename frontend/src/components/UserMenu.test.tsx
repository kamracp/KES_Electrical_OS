// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue, type AuthState } from "../app/authContext";
import { ROLE_LABELS } from "../app/roles";
import { organizationRoleSchema, type OrganizationRole, type Session } from "../services/auth";
import { ApiError } from "../services/http";
import { UserMenu } from "./UserMenu";

function sessionOf(role: OrganizationRole): Session {
  return {
    user: {
      id: "7b0c0a3e-5d0e-4a53-9c58-0d1f6f2f7a11",
      email: "engineer@example.com",
      full_name: "Test Engineer",
      must_change_password: false,
    },
    organization: {
      id: "c1b7f1de-32a4-4c0b-8a4e-3f1f2a9d5b22",
      code: "KES",
      name: "Example Works",
    },
    role,
    session_expires_at: "2026-09-27T10:00:00Z",
    idle_timeout_minutes: 720,
  };
}

function renderMenu(state: AuthState, signOut: AuthContextValue["signOut"] = vi.fn()) {
  const value: AuthContextValue = { state, signIn: vi.fn(), signOut, refresh: vi.fn() };
  render(
    <AuthContext.Provider value={value}>
      <MemoryRouter>
        <UserMenu />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe("UserMenu", () => {
  afterEach(cleanup);

  it("shows who is signed in, with role and organization, and the e-mail as a tooltip", () => {
    renderMenu({ status: "signed-in", session: sessionOf("ENGINEER") });

    const name = screen.getByText("Test Engineer");
    expect(name.getAttribute("title")).toBe("engineer@example.com");
    expect(screen.getByText("Engineer · Example Works")).not.toBeNull();
  });

  it("has a label for every role of the contract", () => {
    expect(Object.keys(ROLE_LABELS).sort()).toEqual([...organizationRoleSchema.options].sort());
  });

  it("links to the change-password page", () => {
    renderMenu({ status: "signed-in", session: sessionOf("OWNER") });

    expect(screen.getByRole("link", { name: "Change password" }).getAttribute("href")).toBe(
      "/change-password",
    );
  });

  it("signs out through the server and locks the button meanwhile", async () => {
    const signOut = vi.fn(() => new Promise<void>(() => {}));
    renderMenu({ status: "signed-in", session: sessionOf("VIEWER") }, signOut);

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    const button = await screen.findByRole("button", { name: "Signing out…" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    expect(signOut).toHaveBeenCalledTimes(1);
  });

  it("says so and stays usable when the sign-out failed", async () => {
    const signOut = vi.fn().mockRejectedValue(new ApiError("Sign-out failed (HTTP 502).", 502));
    renderMenu({ status: "signed-in", session: sessionOf("OWNER") }, signOut);

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect((await screen.findByRole("alert")).textContent).toBe("Sign-out failed (HTTP 502).");
    await waitFor(() =>
      expect((screen.getByRole("button", { name: "Sign out" }) as HTMLButtonElement).disabled).toBe(
        false,
      ),
    );
  });

  it("names the connection when the request itself failed", async () => {
    const signOut = vi.fn().mockRejectedValue(new TypeError("fetch failed"));
    renderMenu({ status: "signed-in", session: sessionOf("OWNER") }, signOut);

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect((await screen.findByRole("alert")).textContent).toBe(
      "Sign-out failed: the server could not be reached.",
    );
  });

  it.each<AuthState>([
    { status: "loading" },
    { status: "signed-out" },
    { status: "error", message: "The session could not be checked." },
  ])("shows nothing while the state is $status", (state) => {
    renderMenu(state);

    expect(document.querySelector("[data-shell-user]")).toBeNull();
  });
});
