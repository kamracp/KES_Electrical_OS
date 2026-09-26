// @vitest-environment jsdom

import { act, cleanup, renderHook } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { AuthContext, type AuthContextValue, type AuthState } from "../app/authContext";
import type { Session } from "../services/auth";
import { clearStudyDrafts, useStudyDraft } from "./useStudyDraft";

const USER_A = "7d1f3a52-4a8e-4f0b-9c61-2b0f8e4d5a10";
const USER_B = "0b9e6c3d-1f2a-4c5b-8d7e-6a5f4e3d2c1b";
const KEY_A = `keos:draft:v1:${USER_A}:transformer`;
const KEY_B = `keos:draft:v1:${USER_B}:transformer`;

type Draft = { code: string; ratings: string[] };

const draftSchema = z.object({ code: z.string(), ratings: z.array(z.string()) });

function createInitial(): Draft {
  return { code: "", ratings: [""] };
}

const OPTIONS = { module: "transformer", createInitial, schema: draftSchema };

function signedIn(userId: string): AuthState {
  const session = {
    user: {
      id: userId,
      email: "engineer@example.com",
      full_name: "Test Engineer",
      must_change_password: false,
    },
    organization: { id: "c1b7f1de-32a4-4c0b-8a4e-3f1f2a9d5b22", code: "KES", name: "KES Works" },
    role: "ENGINEER",
    session_expires_at: "2026-09-27T10:00:00Z",
    idle_timeout_minutes: 720,
  } as Session;
  return { status: "signed-in", session };
}

// The wrapper reads the current auth state on every render, so a test can switch users.
let authState: AuthState = signedIn(USER_A);

function Wrapper({ children }: PropsWithChildren) {
  const auth: AuthContextValue = {
    state: authState,
    signIn: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  };
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

function renderDraft() {
  return renderHook(() => useStudyDraft(OPTIONS), { wrapper: Wrapper });
}

describe("useStudyDraft", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.sessionStorage.clear();
    authState = signedIn(USER_A);
  });

  it("starts from the empty form when nothing is stored", () => {
    const { result } = renderDraft();

    expect(result.current.draft).toEqual(createInitial());
    expect(result.current.restored).toBe(false);
    // An untouched form is not stored.
    expect(window.sessionStorage.getItem(KEY_A)).toBeNull();
  });

  it("restores a stored draft that still matches the schema", () => {
    window.sessionStorage.setItem(KEY_A, JSON.stringify({ code: "TX-01", ratings: ["1000"] }));

    const { result } = renderDraft();

    expect(result.current.draft).toEqual({ code: "TX-01", ratings: ["1000"] });
    expect(result.current.restored).toBe(true);
  });

  it("stops reporting the restore after the first edit", () => {
    window.sessionStorage.setItem(KEY_A, JSON.stringify({ code: "TX-01", ratings: ["1000"] }));
    const { result } = renderDraft();
    expect(result.current.restored).toBe(true);

    act(() => result.current.setDraft((previous) => ({ ...previous, code: "TX-02" })));

    expect(result.current.restored).toBe(false);
    expect(result.current.draft).toEqual({ code: "TX-02", ratings: ["1000"] });
  });

  it("drops a stored draft that is not JSON", () => {
    window.sessionStorage.setItem(KEY_A, "{not json");

    const { result } = renderDraft();

    expect(result.current.draft).toEqual(createInitial());
    expect(result.current.restored).toBe(false);
    expect(window.sessionStorage.getItem(KEY_A)).toBeNull();
  });

  it("drops a stored draft of another shape", () => {
    window.sessionStorage.setItem(KEY_A, JSON.stringify({ code: 7 }));

    const { result } = renderDraft();

    expect(result.current.draft).toEqual(createInitial());
    expect(result.current.restored).toBe(false);
    expect(window.sessionStorage.getItem(KEY_A)).toBeNull();
  });

  it("writes every change", () => {
    const { result } = renderDraft();

    act(() => result.current.setDraft({ code: "TX-01", ratings: [""] }));
    act(() => result.current.setDraft((previous) => ({ ...previous, ratings: ["1000", "1250"] })));

    expect(result.current.draft).toEqual({ code: "TX-01", ratings: ["1000", "1250"] });
    expect(JSON.parse(window.sessionStorage.getItem(KEY_A) ?? "null")).toEqual({
      code: "TX-01",
      ratings: ["1000", "1250"],
    });
  });

  it("clears back to the empty form and forgets the stored draft", () => {
    window.sessionStorage.setItem(KEY_A, JSON.stringify({ code: "TX-01", ratings: ["1000"] }));
    const { result } = renderDraft();

    act(() => result.current.clear());

    expect(result.current.draft).toEqual(createInitial());
    expect(result.current.restored).toBe(false);
    expect(window.sessionStorage.getItem(KEY_A)).toBeNull();
  });

  it("keeps the drafts of two users apart", () => {
    window.sessionStorage.setItem(KEY_B, JSON.stringify({ code: "TX-B", ratings: ["630"] }));
    const { result, rerender } = renderDraft();

    // User A does not see user B's draft ...
    expect(result.current.draft).toEqual(createInitial());
    act(() => result.current.setDraft({ code: "TX-A", ratings: ["1000"] }));

    // ... and when user B signs in on the same tab, B gets B's own draft, not A's entries.
    authState = signedIn(USER_B);
    rerender();

    expect(result.current.draft).toEqual({ code: "TX-B", ratings: ["630"] });
    expect(result.current.restored).toBe(true);
    expect(JSON.parse(window.sessionStorage.getItem(KEY_A) ?? "null")).toEqual({
      code: "TX-A",
      ratings: ["1000"],
    });
  });

  it("writes nothing while nobody is signed in", () => {
    authState = { status: "signed-out" };
    const { result } = renderDraft();

    act(() => result.current.setDraft({ code: "TX-01", ratings: ["1000"] }));

    expect(result.current.draft).toEqual({ code: "TX-01", ratings: ["1000"] });
    expect(window.sessionStorage.length).toBe(0);
  });

  it("keeps working in memory when the storage refuses every access", () => {
    const refused = () => {
      throw new DOMException("refused", "SecurityError");
    };
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(refused);
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(refused);
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(refused);

    const { result } = renderDraft();
    act(() => result.current.setDraft({ code: "TX-01", ratings: ["1000"] }));

    expect(result.current.draft).toEqual({ code: "TX-01", ratings: ["1000"] });
    act(() => result.current.clear());
    expect(result.current.draft).toEqual(createInitial());
  });

  it("clears every draft of one user and only that user", () => {
    window.sessionStorage.setItem(KEY_A, "{}");
    window.sessionStorage.setItem(`keos:draft:v1:${USER_A}:load`, "{}");
    window.sessionStorage.setItem(KEY_B, "{}");
    window.sessionStorage.setItem("keos.project-selection", "{}");

    clearStudyDrafts(USER_A);

    expect(window.sessionStorage.getItem(KEY_A)).toBeNull();
    expect(window.sessionStorage.getItem(`keos:draft:v1:${USER_A}:load`)).toBeNull();
    expect(window.sessionStorage.getItem(KEY_B)).toBe("{}");
    expect(window.sessionStorage.getItem("keos.project-selection")).toBe("{}");
  });
});
