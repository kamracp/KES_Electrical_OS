// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../app/authContext";
import type { OrganizationRole, Session } from "../services/auth";
import { ApiError } from "../services/http";
import {
  createUser,
  listAuthEvents,
  listUsers,
  resetUserPassword,
  updateUser,
  type AuthEvent,
  type User,
} from "../services/users";
import { UsersPage } from "./UsersPage";

vi.mock("../services/users", () => ({
  createUser: vi.fn(),
  listAuthEvents: vi.fn(),
  listUsers: vi.fn(),
  resetUserPassword: vi.fn(),
  updateUser: vi.fn(),
}));

const OWNER_ID = "7b0c0a3e-5d0e-4a53-9c58-0d1f6f2f7a11";

const OWNER: User = {
  id: OWNER_ID,
  email: "owner@example.com",
  full_name: "Olive Owner",
  role: "OWNER",
  is_active: true,
  must_change_password: false,
  locked_until: null,
  last_login_at: "2026-09-20T09:00:00Z",
};

const ENGINEER: User = {
  id: "2f1e0d3c-4b5a-4978-8695-a4b3c2d1e0f9",
  email: "erin@example.com",
  full_name: "Erin Engineer",
  role: "ENGINEER",
  is_active: true,
  must_change_password: true,
  locked_until: null,
  last_login_at: null,
};

const VIEWER_OFF: User = {
  id: "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d",
  email: "vic@example.com",
  full_name: "Vic Viewer",
  role: "VIEWER",
  is_active: false,
  must_change_password: false,
  locked_until: null,
  last_login_at: null,
};

const EVENTS: AuthEvent[] = [
  {
    id: "0d9b1c53-1c0e-4f0b-9a67-5a2f3e4d5c6b",
    event_type: "LOGIN_FAILED",
    user_id: null,
    email_attempted: "nobody@example.com",
    ip_address: "203.0.113.7",
    user_agent: "test agent",
    detail: null,
    occurred_at: "2026-09-20T10:00:00Z",
  },
  {
    id: "1e0a2d64-2d1f-4a1c-8b78-6b3a4f5e6d7c",
    event_type: "USER_CREATED",
    user_id: ENGINEER.id,
    email_attempted: null,
    ip_address: null,
    user_agent: null,
    detail: "role ENGINEER",
    occurred_at: "2026-09-20T09:30:00Z",
  },
];

function sessionOf(role: OrganizationRole): Session {
  return {
    user: {
      id: OWNER_ID,
      email: "owner@example.com",
      full_name: "Olive Owner",
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

function renderPage(role: OrganizationRole = "OWNER") {
  const value: AuthContextValue = {
    state: { status: "signed-in", session: sessionOf(role) },
    signIn: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  };
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={value}>
        <UsersPage />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

async function rowOf(name: string): Promise<HTMLElement> {
  const cell = await screen.findByRole("rowheader", { name: new RegExp(name) });
  const row = cell.closest("tr");
  if (row === null) {
    throw new Error(`no row for ${name}`);
  }
  return row;
}

function fillNewUser(fullName: string, email: string, password: string): void {
  const form = screen.getByRole("group", { name: "New account" });
  fireEvent.change(within(form).getByLabelText("Full name"), { target: { value: fullName } });
  fireEvent.change(within(form).getByLabelText("E-mail"), { target: { value: email } });
  fireEvent.change(within(form).getByLabelText("First password"), { target: { value: password } });
}

describe("UsersPage", () => {
  beforeEach(() => {
    vi.mocked(listUsers).mockReset().mockResolvedValue([OWNER, ENGINEER, VIEWER_OFF]);
    vi.mocked(listAuthEvents).mockReset().mockResolvedValue(EVENTS);
    vi.mocked(createUser).mockReset();
    vi.mocked(updateUser).mockReset();
    vi.mocked(resetUserPassword).mockReset();
  });
  afterEach(cleanup);

  it.each<OrganizationRole>(["ENGINEER", "VIEWER"])(
    "tells a %s that only the owner manages users and asks the server nothing",
    (role) => {
      renderPage(role);

      expect(screen.getByRole("alert").textContent).toBe(
        "Only the owner of the organization can manage users.",
      );
      expect(listUsers).not.toHaveBeenCalled();
      expect(listAuthEvents).not.toHaveBeenCalled();
    },
  );

  it("lists every user with role, status and last sign-in", async () => {
    renderPage();

    const engineer = await rowOf("Erin Engineer");
    expect(within(engineer).getByText("erin@example.com")).not.toBeNull();
    expect(within(engineer).getByText("Password change due")).not.toBeNull();
    expect(within(engineer).getByText("Never")).not.toBeNull();
    expect(
      (within(engineer).getByLabelText("Role of Erin Engineer") as HTMLSelectElement).value,
    ).toBe("ENGINEER");

    const viewer = await rowOf("Vic Viewer");
    expect(within(viewer).getByText("Switched off")).not.toBeNull();
    expect(viewer.getAttribute("data-user-active")).toBe("false");
    expect(within(viewer).getByRole("button", { name: "Switch on" })).not.toBeNull();
  });

  it("keeps the owner from changing, switching off or resetting the own account", async () => {
    renderPage();

    const own = await rowOf("Olive Owner");
    expect(own.textContent).toContain("(you)");
    expect((within(own).getByLabelText("Role of Olive Owner") as HTMLSelectElement).disabled).toBe(
      true,
    );
    expect(within(own).queryByRole("button")).toBeNull();
  });

  it("changes a role and reloads the list", async () => {
    vi.mocked(updateUser).mockResolvedValue({ ...ENGINEER, role: "VIEWER" });
    renderPage();
    const engineer = await rowOf("Erin Engineer");

    fireEvent.change(within(engineer).getByLabelText("Role of Erin Engineer"), {
      target: { value: "VIEWER" },
    });

    expect((await screen.findByRole("status")).textContent).toBe("Erin Engineer is now Viewer.");
    expect(updateUser).toHaveBeenCalledWith(ENGINEER.id, { role: "VIEWER" });
    await waitFor(() => expect(listUsers).toHaveBeenCalledTimes(2));
  });

  it("switches an account off and says that the sessions were closed", async () => {
    vi.mocked(updateUser).mockResolvedValue({ ...ENGINEER, is_active: false });
    renderPage();
    const engineer = await rowOf("Erin Engineer");

    fireEvent.click(within(engineer).getByRole("button", { name: "Switch off" }));

    expect((await screen.findByRole("status")).textContent).toContain("was switched off");
    expect(updateUser).toHaveBeenCalledWith(ENGINEER.id, { is_active: false });
  });

  it("switches an account on again", async () => {
    vi.mocked(updateUser).mockResolvedValue({ ...VIEWER_OFF, is_active: true });
    renderPage();
    const viewer = await rowOf("Vic Viewer");

    fireEvent.click(within(viewer).getByRole("button", { name: "Switch on" }));

    await waitFor(() =>
      expect(updateUser).toHaveBeenCalledWith(VIEWER_OFF.id, { is_active: true }),
    );
  });

  it("shows the server's refusal of a change", async () => {
    vi.mocked(updateUser).mockRejectedValue(
      new ApiError("The organization needs at least one active owner.", 409),
    );
    renderPage();
    const engineer = await rowOf("Erin Engineer");

    fireEvent.click(within(engineer).getByRole("button", { name: "Switch off" }));

    expect((await screen.findByRole("alert")).textContent).toBe(
      "The organization needs at least one active owner.",
    );
  });

  it.each([
    ["", "new@example.com", "a first passphrase", "Full name is required."],
    ["New Person", " ", "a first passphrase", "E-mail is required."],
    [
      "New Person",
      "not-an-address",
      "a first passphrase",
      "Enter a valid e-mail address, for example name@company.com.",
    ],
    [
      "New Person",
      "new@example.com",
      "too short",
      "First password must have at least 12 characters.",
    ],
  ])(
    "refuses a new user %j / %j / %j before anything is sent",
    async (name, email, password, message) => {
      renderPage();
      await rowOf("Olive Owner");
      fillNewUser(name, email, password);

      fireEvent.click(screen.getByRole("button", { name: "Create user" }));

      expect(screen.getByRole("alert").textContent).toBe(message);
      expect(createUser).not.toHaveBeenCalled();
    },
  );

  it("creates a user, clears the form and says what to do with the first password", async () => {
    vi.mocked(createUser).mockResolvedValue({
      ...ENGINEER,
      id: "3c2d1e0f-9a8b-4c7d-8e6f-5a4b3c2d1e0f",
      full_name: "New Person",
      email: "new@example.com",
    });
    renderPage();
    await rowOf("Olive Owner");
    fillNewUser("  New Person ", " new@example.com ", " a first passphrase ");
    fireEvent.change(screen.getByLabelText("Role"), { target: { value: "VIEWER" } });

    fireEvent.click(screen.getByRole("button", { name: "Create user" }));

    expect((await screen.findByRole("status")).textContent).toContain("New Person was created.");
    expect(createUser).toHaveBeenCalledWith({
      full_name: "New Person",
      email: "new@example.com",
      role: "VIEWER",
      password: " a first passphrase ",
    });
    expect((screen.getByLabelText("Full name") as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("First password") as HTMLInputElement).value).toBe("");
    await waitFor(() => expect(listUsers).toHaveBeenCalledTimes(2));
  });

  it("shows the server's message when the e-mail is taken and keeps the form", async () => {
    vi.mocked(createUser).mockRejectedValue(
      new ApiError("A user with this e-mail already exists.", 409),
    );
    renderPage();
    await rowOf("Olive Owner");
    fillNewUser("New Person", "erin@example.com", "a first passphrase");

    fireEvent.click(screen.getByRole("button", { name: "Create user" }));

    expect((await screen.findByRole("alert")).textContent).toBe(
      "A user with this e-mail already exists.",
    );
    expect((screen.getByLabelText("Full name") as HTMLInputElement).value).toBe("New Person");
  });

  it("masks passwords unless the owner asks to see them", async () => {
    renderPage();
    await rowOf("Olive Owner");
    const password = screen.getByLabelText("First password") as HTMLInputElement;
    expect(password.type).toBe("password");

    fireEvent.click(screen.getByLabelText("Show passwords while typing"));

    expect(password.type).toBe("text");
  });

  it("resets a password after checking the rule, then closes the form", async () => {
    vi.mocked(resetUserPassword).mockResolvedValue(undefined);
    renderPage();
    const engineer = await rowOf("Erin Engineer");

    fireEvent.click(within(engineer).getByRole("button", { name: "Reset password" }));
    const form = screen.getByRole("region", { name: "Reset password" });
    fireEvent.change(within(form).getByLabelText("New password"), { target: { value: "short" } });
    fireEvent.click(within(form).getByRole("button", { name: "Reset password" }));

    expect(within(form).getByRole("alert").textContent).toBe(
      "New password must have at least 12 characters.",
    );
    expect(resetUserPassword).not.toHaveBeenCalled();

    fireEvent.change(within(form).getByLabelText("New password"), {
      target: { value: "a new first passphrase" },
    });
    fireEvent.click(within(form).getByRole("button", { name: "Reset password" }));

    expect((await screen.findByRole("status")).textContent).toContain(
      "The password of Erin Engineer was reset",
    );
    expect(resetUserPassword).toHaveBeenCalledWith(ENGINEER.id, "a new first passphrase");
    expect(screen.queryByRole("region", { name: "Reset password" })).toBeNull();
  });

  it("can cancel a password reset", async () => {
    renderPage();
    const engineer = await rowOf("Erin Engineer");
    fireEvent.click(within(engineer).getByRole("button", { name: "Reset password" }));

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("region", { name: "Reset password" })).toBeNull();
  });

  it("shows the audit trail with readable events and the user's name where known", async () => {
    renderPage();

    const trail = await screen.findByRole("region", { name: "Audit trail" });
    const failed = await within(trail).findByText("Sign-in failed");
    const failedRow = failed.closest("tr");
    expect(failedRow?.textContent).toContain("nobody@example.com");
    expect(failedRow?.textContent).toContain("203.0.113.7");

    const created = within(trail).getByText("User created").closest("tr");
    await waitFor(() => expect(created?.textContent).toContain("Erin Engineer"));
    expect(created?.textContent).toContain("role ENGINEER");
    expect(listAuthEvents).toHaveBeenCalledWith(50, expect.anything());
  });

  it("says so when the user list could not be loaded", async () => {
    vi.mocked(listUsers).mockRejectedValue(
      new ApiError("The user list could not be loaded (HTTP 502).", 502),
    );
    renderPage();

    expect((await screen.findByRole("alert")).textContent).toBe(
      "The user list could not be loaded (HTTP 502).",
    );
  });
});
