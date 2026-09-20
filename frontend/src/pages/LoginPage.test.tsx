// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../app/authContext";
import { ApiError } from "../services/http";
import { LoginPage } from "./LoginPage";

function renderPage(signIn: AuthContextValue["signIn"]) {
  const value: AuthContextValue = {
    state: { status: "signed-out" },
    signIn,
    signOut: vi.fn(),
    refresh: vi.fn(),
  };
  render(
    <AuthContext.Provider value={value}>
      <LoginPage />
    </AuthContext.Provider>,
  );
}

function emailInput(): HTMLInputElement {
  return screen.getByLabelText("E-mail") as HTMLInputElement;
}

function passwordInput(): HTMLInputElement {
  return screen.getByLabelText("Password") as HTMLInputElement;
}

function fill(email: string, password: string): void {
  fireEvent.change(emailInput(), { target: { value: email } });
  fireEvent.change(passwordInput(), { target: { value: password } });
}

function submit(): void {
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("LoginPage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("offers an e-mail and a masked password field that password managers understand", () => {
    renderPage(vi.fn());

    expect(screen.getByRole("heading", { name: "Sign in" })).not.toBeNull();
    expect(emailInput().getAttribute("autocomplete")).toBe("username");
    expect(passwordInput().type).toBe("password");
    expect(passwordInput().getAttribute("autocomplete")).toBe("current-password");
  });

  it("asks for the e-mail before anything is sent", () => {
    const signIn = vi.fn();
    renderPage(signIn);
    fill("   ", "a long passphrase");

    submit();

    expect(screen.getByRole("alert").textContent).toBe("E-mail is required.");
    expect(signIn).not.toHaveBeenCalled();
  });

  it("asks for the password before anything is sent", () => {
    const signIn = vi.fn();
    renderPage(signIn);
    fill("engineer@example.com", "");

    submit();

    expect(screen.getByRole("alert").textContent).toBe("Password is required.");
    expect(signIn).not.toHaveBeenCalled();
  });

  it("sends the trimmed e-mail and the password exactly as typed", async () => {
    const signIn = vi.fn(() => new Promise<never>(() => {}));
    renderPage(signIn);
    fill("  engineer@example.com ", " four words and spaces ");

    submit();

    await waitFor(() => expect(signIn).toHaveBeenCalledTimes(1));
    expect(signIn).toHaveBeenCalledWith("engineer@example.com", " four words and spaces ");
  });

  it("locks the button while the request is running", async () => {
    renderPage(vi.fn(() => new Promise<never>(() => {})));
    fill("engineer@example.com", "a long passphrase");

    submit();

    const button = await screen.findByRole("button", { name: "Signing in…" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows the server's message, clears the password and keeps the e-mail", async () => {
    const signIn = vi.fn().mockRejectedValue(new ApiError("Incorrect e-mail or password.", 401));
    renderPage(signIn);
    fill("engineer@example.com", "the wrong passphrase");

    submit();

    expect((await screen.findByRole("alert")).textContent).toBe("Incorrect e-mail or password.");
    expect(passwordInput().value).toBe("");
    expect(emailInput().value).toBe("engineer@example.com");
    expect((screen.getByRole("button", { name: "Sign in" }) as HTMLButtonElement).disabled).toBe(
      false,
    );
    expect(document.activeElement).toBe(passwordInput());
  });

  it("says the server could not be reached when the request itself failed", async () => {
    renderPage(vi.fn().mockRejectedValue(new TypeError("fetch failed")));
    fill("engineer@example.com", "a long passphrase");

    submit();

    expect((await screen.findByRole("alert")).textContent).toBe(
      "The server could not be reached. Check the connection and try again.",
    );
  });

  it("writes nothing to browser storage", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const signIn = vi.fn().mockRejectedValue(new ApiError("Incorrect e-mail or password.", 401));
    renderPage(signIn);
    fill("engineer@example.com", "a long passphrase");

    submit();

    await screen.findByRole("alert");
    expect(setItem).not.toHaveBeenCalled();
  });
});
