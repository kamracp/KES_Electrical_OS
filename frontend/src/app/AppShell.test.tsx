// @vitest-environment jsdom
import { cleanup, render, screen, within } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { AppShell } from "./AppShell";
import { MODULES } from "./modules";

function renderShell(initialEntry: string) {
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
    { initialEntries: [initialEntry] },
  );
  return render(<RouterProvider router={router} />);
}

describe("AppShell", () => {
  afterEach(cleanup);

  it("lists every registry module in the sidebar with its status", () => {
    renderShell("/");
    const nav = screen.getByRole("navigation", { name: "Primary" });
    for (const module of MODULES) {
      const item = nav.querySelector(`[data-module-code="${module.code}"]`);
      expect(item).not.toBeNull();
      expect(item?.querySelector("[data-module-status]")).not.toBeNull();
    }
    expect(nav.querySelector('[data-module-code="EOS-06"] [data-module-status="Live"]')).not.toBeNull();
    expect(
      nav.querySelector('[data-module-code="EOS-05"] [data-module-status="Planned"]'),
    ).not.toBeNull();
  });

  it("links only modules that have a working page", () => {
    renderShell("/");
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getByRole("link", { name: /Cable sizing/ }).getAttribute("href")).toBe(
      "/cable-sizing",
    );
    expect(within(nav).getByRole("link", { name: /Short-circuit study/ }).getAttribute("href")).toBe(
      "/fault-study",
    );
    expect(within(nav).queryByRole("link", { name: /Earthing/ })).toBeNull();
    expect(nav.querySelector('[data-module-code="EOS-08"] [aria-disabled="true"]')).not.toBeNull();
  });

  it("marks the active route and renders the routed page inside the shell", () => {
    renderShell("/cable-sizing");
    expect(screen.getByRole("link", { name: /Cable sizing/ }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getByRole("link", { name: /Home/ }).getAttribute("aria-current")).toBeNull();
    expect(screen.getByText("cable page")).not.toBeNull();
  });

  it("states the engineering basis in the footer", () => {
    renderShell("/");
    const footer = document.querySelector('footer[aria-label="Engineering basis"]');
    expect(footer).not.toBeNull();
    expect(footer?.textContent).toContain("not a statutory compliance certification");
    expect(footer?.textContent).toContain("no manufacturer is named");
  });
});
