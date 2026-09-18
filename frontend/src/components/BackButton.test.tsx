// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { BackButton } from "./BackButton";

function PathProbe() {
  const location = useLocation();
  return <p data-current-path>{location.pathname}</p>;
}

function currentPath(): string | null | undefined {
  return document.querySelector("[data-current-path]")?.textContent;
}

function renderAt(entries: string[], index: number) {
  return render(
    <MemoryRouter initialEntries={entries} initialIndex={index}>
      <BackButton />
      <PathProbe />
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
});

describe("BackButton", () => {
  it("renders nothing on the Home page", () => {
    renderAt(["/"], 0);

    expect(currentPath()).toBe("/");
    expect(screen.queryByRole("button", { name: "Back" })).toBeNull();
  });

  it("goes to the previous in-app page when there is history", async () => {
    renderAt(["/", "/fault", "/cable"], 2);

    expect(currentPath()).toBe("/cable");
    fireEvent.click(screen.getByRole("button", { name: "Back" }));

    await waitFor(() => expect(currentPath()).toBe("/fault"));
    expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument();
  });

  it("falls back to Home when the page was opened directly", async () => {
    renderAt(["/cable"], 0);

    expect(currentPath()).toBe("/cable");
    fireEvent.click(screen.getByRole("button", { name: "Back" }));

    await waitFor(() => expect(currentPath()).toBe("/"));
    expect(screen.queryByRole("button", { name: "Back" })).toBeNull();
  });
});
