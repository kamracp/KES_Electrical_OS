// @vitest-environment jsdom

import { cleanup, render, screen, within } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { AppShell } from "./AppShell";

function renderShellAt(path: string) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <AppShell />,
        children: [
          { index: true, element: <p>home page</p> },
          { path: "cable-sizing", element: <p>cable page</p> },
          { path: "fault-study", element: <p>fault page</p> },
        ],
      },
    ],
    { initialEntries: [path] },
  );
  return render(<RouterProvider router={router} />);
}

afterEach(() => {
  cleanup();
});

describe("AppShell", () => {
  it("renders primary navigation with module codes and truthful status", () => {
    renderShellAt("/");
    const nav = screen.getByRole("navigation", { name: "Primary" });

    expect(within(nav).getByRole("link", { name: "Home" }).getAttribute("href")).toBe("/");
    expect(within(nav).getByRole("link", { name: "Cable Sizing" }).getAttribute("href")).toBe(
      "/cable-sizing",
    );
    expect(within(nav).getByRole("link", { name: "Fault Study" }).getAttribute("href")).toBe(
      "/fault-study",
    );
    expect(nav.querySelector('[data-module-code="EOS-06"] [data-module-status="Live"]')).not.toBeNull();
    expect(
      nav.querySelector('[data-module-code="EOS-04"] [data-module-status="Live"]'),
    ).not.toBeNull();
  });

  it("marks the active route and renders the routed page inside the shell", () => {
    renderShellAt("/cable-sizing");

    expect(screen.getByRole("link", { name: "Cable Sizing" }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getByRole("link", { name: "Home" }).getAttribute("aria-current")).toBeNull();
    expect(screen.getByText("cable page")).not.toBeNull();
  });

  it("states the engineering basis in the footer", () => {
    renderShellAt("/");
    const footer = screen.getByRole("contentinfo", { name: "Engineering basis" });

    expect(footer.textContent).toContain("not a statutory compliance certification");
    expect(footer.textContent).toContain("no manufacturer is named");
  });
});
