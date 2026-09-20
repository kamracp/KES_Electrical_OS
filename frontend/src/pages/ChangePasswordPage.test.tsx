// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../app/authContext";
import { changePassword, type Session } from "../services/auth";
import { ApiError } from "../services/http";
import { ChangePasswordPage } from "./ChangePasswordPage";

vi.mock("../services/auth", () => ({ changePassword: vi.fn() }));

const CURRENT = "the first password";
const NEXT = "four new words with spaces";

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

function renderPage(mustChangePassword: boolean, overrides: Partial<AuthContextValue> = {}) {
  const value: AuthContextValue = {
    state: { status: "signed-in", session: sessionOf(mustChangePassword) },
    signIn: vi.fn(),
    signOut: vi.fn(async () => {}),
    refresh: vi.fn(async () => {}),
    ...overrides,
  };
  render(
    <AuthContext.Provider value={value}>
      <MemoryRouter>
        <ChangePasswordPage />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
  return value;
}

function field(label: string): HTMLInputElement {
  return screen.getByLabelText(label) as HTMLInputElement;
}

function fill(current: string, next: string, repeat: string): void {
  fireEvent.change(field("Current password"), { target: { value: current } });
  fireEvent.change(field("New password"), { target: { value: next } });
  fireEvent.change(field("Repeat new password"), { target: { value: repeat } });
}

function submit(): void {
  fireEvent.click(screen.getByRole("button", { name: "Change password" }));
}

describe("ChangePasswordPage", () => {
  beforeEach(() => {
    vi.mocked(changePassword).mockReset();
  });
  afterEach(cleanup);

  it("tells a user with a first or reset password why they are here, with no way round", () => {
    renderPage(true);

    expect(screen.getByText(/must be changed before any study can be opened/)).not.toBeNull();
    expect(screen.queryByRole("link", { name: "Back to Home" })).toBeNull();
    expect(screen.getByRole("button", { name: "Sign out" })).not.toBeNull();
  });

  it("lets a user with nothing due go back to Home", () => {
    renderPage(false);

    expect(screen.queryByText(/must be changed before/)).toBeNull();
    expect(screen.getByRole("link", { name: "Back to Home" }).getAttribute("href")).toBe("/");
  });

  it("masks all three fields and marks them for password managers", () => {
    renderPage(false);

    expect(field("Current password").type).toBe("password");
    expect(field("Current password").getAttribute("autocomplete")).toBe("current-password");
    expect(field("New password").getAttribute("autocomplete")).toBe("new-password");
    expect(field("Repeat new password").getAttribute("autocomplete")).toBe("new-password");
  });

  it.each([
    ["", NEXT, NEXT, "Current password is required."],
    [CURRENT, "", "", "New password is required."],
    [CURRENT, "too short", "too short", "New password must have at least 12 characters."],
    [CURRENT, "x".repeat(129), "x".repeat(129), "New password must have at most 128 characters."],
    [CURRENT, " ".repeat(12), " ".repeat(12), "New password must not be blank."],
    [
      CURRENT,
      "Engineer@Example.com",
      "Engineer@Example.com",
      "New password must not be the e-mail address.",
    ],
    [CURRENT, CURRENT, CURRENT, "New password must differ from the current password."],
    [CURRENT, NEXT, `${NEXT} `, "The two new passwords do not match."],
  ])("refuses %j / %j / %j before anything is sent", (current, next, repeat, message) => {
    renderPage(false);
    fill(current, next, repeat);

    submit();

    expect(screen.getByRole("alert").textContent).toBe(message);
    expect(changePassword).not.toHaveBeenCalled();
  });

  it("changes the password, refreshes the session and confirms", async () => {
    vi.mocked(changePassword).mockResolvedValue(undefined);
    const value = renderPage(true);
    fill(CURRENT, NEXT, NEXT);

    submit();

    expect((await screen.findByRole("status")).textContent).toContain(
      "Your password has been changed.",
    );
    expect(changePassword).toHaveBeenCalledWith(CURRENT, NEXT);
    await waitFor(() => expect(value.refresh).toHaveBeenCalledTimes(1));
    expect(screen.queryByLabelText("New password")).toBeNull();
    expect(screen.getByRole("link", { name: "Continue to Home" }).getAttribute("href")).toBe("/");
  });

  it("shows the server's refusal, clears every field and does not refresh", async () => {
    vi.mocked(changePassword).mockRejectedValue(
      new ApiError("The current password is not correct.", 400),
    );
    const value = renderPage(false);
    fill("not the current one", NEXT, NEXT);

    submit();

    expect((await screen.findByRole("alert")).textContent).toBe(
      "The current password is not correct.",
    );
    expect(field("Current password").value).toBe("");
    expect(field("New password").value).toBe("");
    expect(field("Repeat new password").value).toBe("");
    expect(value.refresh).not.toHaveBeenCalled();
  });

  it("signs out from this page", async () => {
    const value = renderPage(true);

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => expect(value.signOut).toHaveBeenCalledTimes(1));
  });

  it("says so when the sign-out failed", async () => {
    renderPage(true, {
      signOut: vi.fn().mockRejectedValue(new ApiError("Sign-out failed (HTTP 502).", 502)),
    });

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect((await screen.findByRole("alert")).textContent).toBe("Sign-out failed (HTTP 502).");
  });
});
