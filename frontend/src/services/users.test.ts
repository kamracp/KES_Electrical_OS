import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createUser,
  listAuthEvents,
  listUsers,
  resetUserPassword,
  updateUser,
  type User,
} from "./users";

const USER: User = {
  id: "7b0c0a3e-5d0e-4a53-9c58-0d1f6f2f7a11",
  email: "engineer@example.com",
  full_name: "Test Engineer",
  role: "ENGINEER",
  is_active: true,
  must_change_password: true,
  locked_until: null,
  last_login_at: null,
};

const EVENT = {
  id: "0d9b1c53-1c0e-4f0b-9a67-5a2f3e4d5c6b",
  event_type: "LOGIN_FAILED",
  user_id: null,
  email_attempted: "nobody@example.com",
  ip_address: "203.0.113.7",
  user_agent: "test agent",
  detail: null,
  occurred_at: "2026-09-20T10:00:00Z",
};

const fetchMock = vi.fn<typeof fetch>();

function lastRequest(): { url: string; init: RequestInit } {
  const call = fetchMock.mock.calls.at(-1);
  if (call === undefined) {
    throw new Error("fetch was not called");
  }
  return { url: String(call[0]), init: call[1] ?? {} };
}

describe("users service", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists the users of the organization", async () => {
    fetchMock.mockResolvedValue(Response.json({ items: [USER], total: 1 }));

    await expect(listUsers()).resolves.toEqual([USER]);
    expect(lastRequest().url).toBe("/api/v1/users");
    expect(lastRequest().init.method).toBe("GET");
    expect(lastRequest().init.credentials).toBe("same-origin");
  });

  it("refuses a user list with a field it does not know (a hash must never pass)", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ items: [{ ...USER, password_hash: "x" }], total: 1 }),
    );

    await expect(listUsers()).rejects.toThrow("Unexpected response");
  });

  it("rejects with the status when the server refuses (not an owner)", async () => {
    fetchMock.mockResolvedValue(Response.json({ detail: "Owner role required." }, { status: 403 }));

    await expect(listUsers()).rejects.toMatchObject({
      name: "ApiError",
      status: 403,
      message: "Owner role required.",
    });
  });

  it("loads the audit trail with the limit", async () => {
    fetchMock.mockResolvedValue(Response.json({ items: [EVENT] }));

    await expect(listAuthEvents(25)).resolves.toEqual([EVENT]);
    expect(lastRequest().url).toBe("/api/v1/users/events?limit=25");
  });

  it("creates a user whose first password must be changed", async () => {
    fetchMock.mockResolvedValue(Response.json(USER, { status: 201 }));

    await createUser({
      email: "engineer@example.com",
      full_name: "Test Engineer",
      role: "ENGINEER",
      password: "a first passphrase",
    });

    expect(lastRequest().init.method).toBe("POST");
    expect(JSON.parse(String(lastRequest().init.body))).toEqual({
      email: "engineer@example.com",
      full_name: "Test Engineer",
      role: "ENGINEER",
      password: "a first passphrase",
      must_change_password: true,
    });
  });

  it("passes on the server's message when the e-mail is taken", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "A user with this e-mail already exists." }, { status: 409 }),
    );

    await expect(
      createUser({ email: "a@b.co", full_name: "A", role: "VIEWER", password: "a first passphrase" }),
    ).rejects.toMatchObject({ status: 409, message: "A user with this e-mail already exists." });
  });

  it("sends only the change to the user's address", async () => {
    fetchMock.mockResolvedValue(Response.json({ ...USER, is_active: false }));

    const changed = await updateUser(USER.id, { is_active: false });

    expect(changed.is_active).toBe(false);
    expect(lastRequest().url).toBe(`/api/v1/users/${USER.id}`);
    expect(lastRequest().init.method).toBe("PATCH");
    expect(JSON.parse(String(lastRequest().init.body))).toEqual({ is_active: false });
  });

  it("resets a password (the server answers with no content)", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await expect(resetUserPassword(USER.id, "a new first passphrase")).resolves.toBeUndefined();
    expect(lastRequest().url).toBe(`/api/v1/users/${USER.id}/password`);
    expect(JSON.parse(String(lastRequest().init.body))).toEqual({
      new_password: "a new first passphrase",
    });
  });

  it("passes on the refusal to reset the own password", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "Use Change password for your own account." }, { status: 409 }),
    );

    await expect(resetUserPassword(USER.id, "a new first passphrase")).rejects.toMatchObject({
      status: 409,
      message: "Use Change password for your own account.",
    });
  });
});
