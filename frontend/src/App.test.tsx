// @vitest-environment jsdom

import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { AppProviders } from "./app/providers";

vi.mock("./services/health", () => ({
  getHealth: vi.fn(() =>
    Promise.resolve({ status: "healthy", application: "KES Electrical OS API" }),
  ),
}));

function renderHome() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </AppProviders>,
  );
}

afterEach(() => {
  cleanup();
});

describe("App home page", () => {
  it("lists modules with status and links only the working pages", () => {
    renderHome();
    const modules = screen.getByRole("region", { name: "Modules" });

    const cable = modules.querySelector('[data-module-code="EOS-06"]') as HTMLElement;
    expect(cable.getAttribute("data-module-status")).toBe("Live");
    expect(within(cable).getByRole("link", { name: "Open Cable Sizing" }).getAttribute("href")).toBe(
      "/cable-sizing",
    );

    const fault = modules.querySelector('[data-module-code="EOS-04"]') as HTMLElement;
    expect(fault.getAttribute("data-module-status")).toBe("Live");
    expect(within(fault).getByRole("link", { name: "Open Fault Study" })).not.toBeNull();

    const loads = modules.querySelector('[data-module-code="EOS-02"]') as HTMLElement;
    expect(loads.getAttribute("data-module-status")).toBe("Backend only");
    expect(within(loads).queryByRole("link")).toBeNull();
  });

  it("keeps the workspace heading and the API health status", () => {
    renderHome();

    expect(screen.getByRole("heading", { level: 1, name: "KES Electrical OS" })).not.toBeNull();
    expect(screen.getByRole("heading", { name: "Electrical Engineering Workspace" })).not.toBeNull();
  });
});
