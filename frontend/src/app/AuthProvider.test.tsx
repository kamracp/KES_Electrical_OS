// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider, useMutation, useQuery } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getSession, signIn, signOut, type Session } from "../services/auth";
import { ApiError } from "../services/http";
import { AuthProvider } from "./AuthProvider";
import { SESSION_QUERY_KEY, useAuth } from "./authContext";

vi.mock("../services/auth", () => ({
  getSession: vi.fn(),
  signIn: vi.fn(),
  signOut: vi.fn(),
}));

const SESSION: Session = {
  user: {
    id: "7b0c0a3e-5d0e-4a53-9c58-0d1f6f2f7a11",
    email: "engineer@example.com",
    full_name: "Test Engineer",
    must_change_password: false,
  },
  organization: { id: "c1b7f1de-32a4-4c0b-8a4e-3f1f2a9d5b22", code: "KES", name: "KES" },
  role: "ENGINEER",
  session_expires_at: "2026-09-27T10:00:00Z",
  idle_timeout_minutes: 720,
};

const STUDY_KEY = ["cable", "runs"];

function Probe() {
  const { state, signIn: doSignIn, signOut: doSignOut, refresh } = useAuth();

  return (
    <div>
      <p data-testid="status">{state.status}</p>
      <p data-testid="detail">
        {state.status === "signed-in" ? state.session.user.full_name : ""}
        {state.status === "error" ? state.message : ""}
      </p>
      <button
        type="button"
        onClick={() => void doSignIn("engineer@example.com", "a long passphrase").catch(() => {})}
      >
        sign in
      </button>
      <button type="button" onClick={() => void doSignOut().catch(() => {})}>
        sign out
      </button>
      <button type="button" onClick={() => void refresh()}>
        refresh
      </button>
    </div>
  );
}

// Stands for a study page: one mutation and one query that fail the way the test says.
function StudyProbe({ failure }: { failure: unknown }) {
  const mutation = useMutation<void, unknown, void>({
    mutationFn: () => Promise.reject(failure),
  });
  const query = useQuery({
    queryKey: ["study", "probe"],
    queryFn: () => Promise.reject(failure),
    enabled: false,
  });

  return (
    <div>
      <button type="button" onClick={() => mutation.mutate()}>
        calculate
      </button>
      <button type="button" onClick={() => void query.refetch()}>
        load
      </button>
      <p data-testid="calculation">{mutation.isError ? "failed" : "idle"}</p>
    </div>
  );
}

function renderWithStudy(failure: unknown) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Probe />
        <StudyProbe failure={failure} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

function renderProvider() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </QueryClientProvider>,
  );
  return queryClient;
}

function status(): string | null {
  return screen.getByTestId("status").textContent;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.mocked(getSession).mockReset();
    vi.mocked(signIn).mockReset();
    vi.mocked(signOut).mockReset();
  });
  afterEach(cleanup);

  it("is loading first, then signed out when the server says nobody is signed in", async () => {
    vi.mocked(getSession).mockResolvedValue(null);
    renderProvider();

    expect(status()).toBe("loading");
    await waitFor(() => expect(status()).toBe("signed-out"));
  });

  it("is signed in with the session the server returned", async () => {
    vi.mocked(getSession).mockResolvedValue(SESSION);
    renderProvider();

    await waitFor(() => expect(status()).toBe("signed-in"));
    expect(screen.getByTestId("detail").textContent).toBe("Test Engineer");
  });

  it("reports a failed session check as an error, never as signed in, and can retry", async () => {
    vi.mocked(getSession).mockRejectedValueOnce(new Error("The session could not be checked."));
    renderProvider();

    await waitFor(() => expect(status()).toBe("error"));
    expect(screen.getByTestId("detail").textContent).toBe("The session could not be checked.");

    vi.mocked(getSession).mockResolvedValue(SESSION);
    fireEvent.click(screen.getByRole("button", { name: "refresh" }));

    await waitFor(() => expect(status()).toBe("signed-in"));
  });

  it("keeps the user signed in when a background re-check fails", async () => {
    vi.mocked(getSession).mockResolvedValueOnce(SESSION);
    renderProvider();
    await waitFor(() => expect(status()).toBe("signed-in"));

    vi.mocked(getSession).mockRejectedValueOnce(new Error("network down"));
    fireEvent.click(screen.getByRole("button", { name: "refresh" }));

    await waitFor(() => expect(getSession).toHaveBeenCalledTimes(2));
    expect(status()).toBe("signed-in");
  });

  it("signs out when a re-check says the session has ended", async () => {
    vi.mocked(getSession).mockResolvedValueOnce(SESSION);
    renderProvider();
    await waitFor(() => expect(status()).toBe("signed-in"));

    vi.mocked(getSession).mockResolvedValueOnce(null);
    fireEvent.click(screen.getByRole("button", { name: "refresh" }));

    await waitFor(() => expect(status()).toBe("signed-out"));
  });

  it("signs in without a second session request and drops data cached before", async () => {
    vi.mocked(getSession).mockResolvedValue(null);
    vi.mocked(signIn).mockResolvedValue(SESSION);
    const queryClient = renderProvider();
    await waitFor(() => expect(status()).toBe("signed-out"));
    queryClient.setQueryData(STUDY_KEY, ["run of the previous user"]);

    fireEvent.click(screen.getByRole("button", { name: "sign in" }));

    await waitFor(() => expect(status()).toBe("signed-in"));
    expect(signIn).toHaveBeenCalledWith("engineer@example.com", "a long passphrase");
    expect(getSession).toHaveBeenCalledTimes(1);
    expect(queryClient.getQueryData(STUDY_KEY)).toBeUndefined();
    expect(queryClient.getQueryData(SESSION_QUERY_KEY)).toEqual(SESSION);
  });

  it("stays signed out when the server refuses the credentials", async () => {
    vi.mocked(getSession).mockResolvedValue(null);
    vi.mocked(signIn).mockRejectedValue(new Error("Incorrect e-mail or password."));
    renderProvider();
    await waitFor(() => expect(status()).toBe("signed-out"));

    fireEvent.click(screen.getByRole("button", { name: "sign in" }));

    await waitFor(() => expect(signIn).toHaveBeenCalledTimes(1));
    expect(status()).toBe("signed-out");
  });

  it("signs out on the server, then forgets the session and cached study data", async () => {
    vi.mocked(getSession).mockResolvedValue(SESSION);
    vi.mocked(signOut).mockResolvedValue(undefined);
    const queryClient = renderProvider();
    await waitFor(() => expect(status()).toBe("signed-in"));
    queryClient.setQueryData(STUDY_KEY, ["run of this user"]);

    fireEvent.click(screen.getByRole("button", { name: "sign out" }));

    await waitFor(() => expect(status()).toBe("signed-out"));
    expect(signOut).toHaveBeenCalledTimes(1);
    expect(queryClient.getQueryData(STUDY_KEY)).toBeUndefined();
  });

  it("stays signed in when the server could not close the session", async () => {
    vi.mocked(getSession).mockResolvedValue(SESSION);
    vi.mocked(signOut).mockRejectedValue(new Error("Sign-out failed (HTTP 502)."));
    const queryClient = renderProvider();
    await waitFor(() => expect(status()).toBe("signed-in"));
    queryClient.setQueryData(STUDY_KEY, ["run of this user"]);

    fireEvent.click(screen.getByRole("button", { name: "sign out" }));

    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1));
    expect(status()).toBe("signed-in");
    expect(queryClient.getQueryData(STUDY_KEY)).toEqual(["run of this user"]);
  });

  it("refuses to be used outside the provider", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<Probe />)).toThrow("useAuth must be used inside <AuthProvider>.");

    consoleError.mockRestore();
  });
});

describe("AuthProvider - an API call that is refused", () => {
  beforeEach(() => {
    vi.mocked(getSession).mockReset();
  });
  afterEach(cleanup);

  it("signs out when a calculation comes back with HTTP 401", async () => {
    vi.mocked(getSession).mockResolvedValueOnce(SESSION).mockResolvedValue(null);
    renderWithStudy(new ApiError("Not signed in.", 401));
    await waitFor(() => expect(status()).toBe("signed-in"));

    fireEvent.click(screen.getByRole("button", { name: "calculate" }));

    await waitFor(() => expect(status()).toBe("signed-out"));
    expect(screen.getByTestId("calculation").textContent).toBe("failed");
    expect(getSession).toHaveBeenCalledTimes(2);
  });

  it("signs out when a data request comes back with HTTP 401", async () => {
    vi.mocked(getSession).mockResolvedValueOnce(SESSION).mockResolvedValue(null);
    renderWithStudy(new ApiError("Not signed in.", 401));
    await waitFor(() => expect(status()).toBe("signed-in"));

    fireEvent.click(screen.getByRole("button", { name: "load" }));

    await waitFor(() => expect(status()).toBe("signed-out"));
  });

  it("asks the server again after HTTP 403 and sees a password change that is due", async () => {
    const changeDue: Session = {
      ...SESSION,
      user: { ...SESSION.user, must_change_password: true },
    };
    vi.mocked(getSession).mockResolvedValueOnce(SESSION).mockResolvedValue(changeDue);
    renderWithStudy(new ApiError("Change your password first.", 403));
    await waitFor(() => expect(status()).toBe("signed-in"));

    fireEvent.click(screen.getByRole("button", { name: "calculate" }));

    await waitFor(() => expect(getSession).toHaveBeenCalledTimes(2));
    expect(status()).toBe("signed-in");
  });

  it.each([
    ["a validation refusal (HTTP 422)", new ApiError("Study code is required.", 422)],
    ["a server failure (HTTP 502)", new ApiError("Cable sizing failed (HTTP 502).", 502)],
    ["a failure without a status", new Error("fetch failed")],
  ])("leaves the session alone after %s", async (_label, failure) => {
    vi.mocked(getSession).mockResolvedValue(SESSION);
    renderWithStudy(failure);
    await waitFor(() => expect(status()).toBe("signed-in"));

    fireEvent.click(screen.getByRole("button", { name: "calculate" }));

    await waitFor(() => expect(screen.getByTestId("calculation").textContent).toBe("failed"));
    expect(getSession).toHaveBeenCalledTimes(1);
    expect(status()).toBe("signed-in");
  });

  it("does not ask again without end when the session request itself is refused", async () => {
    vi.mocked(getSession).mockRejectedValue(new ApiError("Forbidden.", 403));
    renderWithStudy(new Error("not used"));

    await waitFor(() => expect(status()).toBe("error"));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(getSession).toHaveBeenCalledTimes(1);
  });
});
