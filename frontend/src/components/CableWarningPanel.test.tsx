// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { CableEngineeringWarning } from "../services/cable";
import { CableWarningPanel } from "./CableWarningPanel";

afterEach(() => {
  cleanup();
});

const warnings: CableEngineeringWarning[] = [
  {
    code: "VOLTAGE_DROP_EXCEEDED",
    message: "Voltage drop 6.20 % exceeds the allowable 5.00 %.",
    field_name: "circuit.route_length_m",
  },
  {
    code: "SOIL_DATA_REQUIRED",
    message: "Soil thermal resistivity is required for buried installation.",
    field_name: null,
  },
  {
    code: "SOIL_DATA_REQUIRED",
    message: "Burial depth is required for buried installation.",
    field_name: "installation.burial_depth_m",
  },
];

function panel(): HTMLElement {
  return screen.getByRole("region", { name: "Engineering warnings" });
}

describe("CableWarningPanel", () => {
  it("announces when no warnings were raised and renders no list", () => {
    render(<CableWarningPanel warnings={[]} />);

    const section = panel();
    expect(within(section).getByText("No engineering warnings raised.")).toHaveAttribute(
      "data-no-warnings",
      "true",
    );
    expect(within(section).queryByRole("list")).toBeNull();
  });

  it("renders one item per warning with a human label and the backend message", () => {
    render(<CableWarningPanel warnings={warnings} />);

    const list = within(panel()).getByRole("list");
    expect(list).toHaveAttribute("data-warning-count", "3");
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(3);

    expect(items[0]).toHaveAttribute("data-warning-code", "VOLTAGE_DROP_EXCEEDED");
    expect(items[0]).toHaveTextContent("Voltage drop exceeded");
    expect(items[0]).toHaveTextContent("Voltage drop 6.20 % exceeds the allowable 5.00 %.");
  });

  it("shows the field name only when the warning names a field", () => {
    render(<CableWarningPanel warnings={warnings} />);

    const items = within(within(panel()).getByRole("list")).getAllByRole("listitem");

    expect(items[0].querySelector("[data-warning-field]")).toHaveAttribute(
      "data-warning-field",
      "circuit.route_length_m",
    );
    expect(items[0]).toHaveTextContent("Field: circuit.route_length_m");

    expect(items[1]).toHaveAttribute("data-warning-code", "SOIL_DATA_REQUIRED");
    expect(items[1].querySelector("[data-warning-field]")).toBeNull();
    expect(items[1]).not.toHaveTextContent("Field:");
  });

  it("keeps repeated warning codes as separate items", () => {
    render(<CableWarningPanel warnings={warnings} />);

    const repeated = panel().querySelectorAll('[data-warning-code="SOIL_DATA_REQUIRED"]');
    expect(repeated).toHaveLength(2);
    expect(repeated[1]).toHaveTextContent("Burial depth is required for buried installation.");
    expect(repeated[1].querySelector("[data-warning-field]")).toHaveAttribute(
      "data-warning-field",
      "installation.burial_depth_m",
    );
  });
});
