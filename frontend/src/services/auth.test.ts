// @vitest-environment node

import { afterEach, describe, expect, it, vi } from "vitest";

import { changePassword, getSession, signIn, signOut, type Session } from "./auth";
import { ApiError } from "./http";

const session: Session = {
  user: {
    id: "7d1f6c0e-3b0a-4a7e-9c55-2f4b8f1f0a11",
    email: "owner@example.com",
    full_name: "Test Owner",
    must_change_password: false,
  },
  organization: {
    id: "0a9c4f5e-1d2b-4c3a-8e7f-6b5a4d3c2b1a",
    code: "KES",
    name: "Kamra Engineering Solutions",
  },
  role: "OWNER",
  session_expires_at: "2026-09-27T09:00:00Z",
  idle_timeout_minutes: 720,
};

const SIGN_IN_FAILED =
  "Sign-in failed. Check the e-mail and the password; after 5 failed attempts an account is locked for 15 minutes.";

function stubFetch(response: () => Response) {
  const fetchMock = vi.fn<typeof fetch>(async () => response());
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("auth service", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("signs in with e-mail and password in the request body only", async () => {
    const fetchMock = stubFetch(() => Response.json(session));

    await expect(signIn("owner@example.com", "correct horse battery staple")).resolves.toEqual(
      session,
    );

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/auth/login");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({
      email: "owner@example.com",
      password: "correct horse battery staple",
    });
  });

  it("reports a refused sign-in with the server's sentence and the status", async () => {
    stubFetch(() => Response.json({ detail: SIGN_IN_FAILED }, { status: 401 }));

    const error = await signIn("owner@example.com", "wrong").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(401);
    expect((error as ApiError).message).toBe(SIGN_IN_FAILED);
  });

  it("rejects a sign-in answer that is not a session", async () => {
    stubFetch(() => Response.json({ ...session, token: "must-never-be-here" }));

    await expect(signIn("owner@example.com", "x")).rejects.toThrow(
      "Unexpected response from the KES Electrical OS sign-in API.",
    );
  });

  it("returns the session when signed in and null when not", async () => {
    stubFetch(() => Response.json(session));
    await expect(getSession()).resolves.toEqual(session);

    stubFetch(() => Response.json({ detail: "Sign in to continue." }, { status: 401 }));
    await expect(getSession()).resolves.toBeNull();
  });

  it("does not mistake a server failure for being signed out", async () => {
    stubFetch(() => new Response("bad gateway", { status: 502 }));

    const error = await getSession().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(502);
    expect((error as ApiError).message).toBe("The session could not be checked (HTTP 502).");
  });

  it("signs out with a POST and accepts the empty answer", async () => {
    const fetchMock = stubFetch(() => new Response(null, { status: 204 }));

    await expect(signOut()).resolves.toBeUndefined();

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/auth/logout");
    expect(init?.method).toBe("POST");
  });

  it("changes the password and passes refusals on in readable words", async () => {
    const fetchMock = stubFetch(() => new Response(null, { status: 204 }));
    await expect(
      changePassword("old passphrase here", "new passphrase here"),
    ).resolves.toBeUndefined();
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/auth/password");
    expect(JSON.parse(String(init?.body))).toEqual({
      current_password: "old passphrase here",
      new_password: "new passphrase here",
    });

    stubFetch(() =>
      Response.json({ detail: "The current password is not correct." }, { status: 400 }),
    );
    await expect(changePassword("x", "new passphrase here")).rejects.toThrow(
      "The current password is not correct.",
    );

    stubFetch(() =>
      Response.json({ detail: "Password must have at least 12 characters." }, { status: 422 }),
    );
    await expect(changePassword("old passphrase here", "short")).rejects.toThrow(
      "Password must have at least 12 characters.",
    );
  });
});
