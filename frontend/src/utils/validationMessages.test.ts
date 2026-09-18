import { describe, expect, it } from "vitest";

import {
  describeLocation,
  describeValidationIssue,
  type ValidationIssueLike,
  type ValidationLabels,
} from "./validationMessages";

const labels: ValidationLabels = {
  fields: {
    "cable.number_of_loaded_conductors": "Loaded conductors",
    "sources.*.name": "Name",
    sources: "Sources",
    utilization: "Utilization",
  },
  groups: { sources: "Source" },
};

function issue(path: PropertyKey[], rest: Partial<ValidationIssueLike> = {}): ValidationIssueLike {
  return { path, message: "raw message", ...rest };
}

describe("describeLocation", () => {
  it("uses the form label for a plain field", () => {
    expect(describeLocation(["cable", "number_of_loaded_conductors"], labels)).toBe(
      "Loaded conductors",
    );
  });

  it("numbers list items from one and uses the group name", () => {
    expect(describeLocation(["sources", 0, "name"], labels)).toBe("Source 1 — Name");
  });

  it("falls back to readable words when no label is registered", () => {
    expect(describeLocation(["branches", 2, "from_bus_code"])).toBe("Branch 3 — From bus code");
    expect(describeLocation(["buses", 0, "nominal_voltage_v"])).toBe("Bus 1 — Nominal voltage v");
  });

  it("names only the item when the path ends at a list index", () => {
    expect(describeLocation(["sources", 1], labels)).toBe("Source 2");
  });

  it("returns an empty string for an empty path", () => {
    expect(describeLocation([], labels)).toBe("");
  });
});

describe("describeValidationIssue", () => {
  it("rewrites the raw Cable message the founder saw", () => {
    const raw = issue(["cable", "number_of_loaded_conductors"], {
      code: "too_small",
      origin: "number",
      minimum: 1,
      inclusive: true,
      message: "Too small: expected number to be >=1",
    });
    expect(describeValidationIssue(raw, labels)).toBe("Loaded conductors must be at least 1.");
  });

  it("rewrites the raw Fault message the founder saw", () => {
    const raw = issue(["sources", 0, "name"], {
      code: "too_small",
      origin: "string",
      minimum: 1,
      inclusive: true,
      message: "Too small: expected string to have >=1 characters",
    });
    expect(describeValidationIssue(raw, labels)).toBe("Source 1 — Name is required.");
  });

  it("states an exclusive minimum as greater than", () => {
    const raw = issue(["utilization"], {
      code: "too_small",
      origin: "number",
      minimum: 0,
      inclusive: false,
    });
    expect(describeValidationIssue(raw, labels)).toBe("Utilization must be greater than 0.");
  });

  it.each<[string, Partial<ValidationIssueLike>, string]>([
    ["inclusive", { inclusive: true }, "Utilization must be at most 1."],
    ["exclusive", { inclusive: false }, "Utilization must be less than 1."],
  ])("states an %s maximum", (_name, rest, expected) => {
    const raw = issue(["utilization"], { code: "too_big", origin: "number", maximum: 1, ...rest });
    expect(describeValidationIssue(raw, labels)).toBe(expected);
  });

  it.each<[string, Partial<ValidationIssueLike>, string]>([
    ["minimum", { code: "too_small", minimum: 3 }, "Code must have at least 3 characters."],
    ["maximum", { code: "too_big", maximum: 40 }, "Code must have at most 40 characters."],
  ])("states a string length %s", (_name, rest, expected) => {
    expect(describeValidationIssue(issue(["code"], { origin: "string", ...rest }))).toBe(expected);
  });

  it.each<[number, string]>([
    [1, "Sources needs at least 1 entry."],
    [2, "Sources needs at least 2 entries."],
  ])("states a list minimum of %s", (minimum, expected) => {
    const raw = issue(["sources"], { code: "too_small", origin: "array", minimum });
    expect(describeValidationIssue(raw, labels)).toBe(expected);
  });

  it("calls a missing value required", () => {
    const raw = issue(["sources", 0, "name"], {
      code: "invalid_type",
      expected: "string",
      message: "Invalid input: expected string, received undefined",
    });
    expect(describeValidationIssue(raw, labels)).toBe("Source 1 — Name is required.");
  });

  it("asks for a number when the input is not one", () => {
    const raw = issue(["utilization"], {
      code: "invalid_type",
      expected: "number",
      message: "Invalid input: expected number, received NaN",
    });
    expect(describeValidationIssue(raw, labels)).toBe("Utilization must be a number.");
  });

  it.each(["invalid_value", "invalid_enum_value"])("points to the options for %s", (code) => {
    expect(describeValidationIssue(issue(["fault_type"], { code }))).toBe(
      "Fault type must be one of the listed options.",
    );
  });

  it("keeps the message of an unknown issue kind after the label", () => {
    const raw = issue(["sources", 1], { code: "custom", message: "Give an impedance or a current." });
    expect(describeValidationIssue(raw, labels)).toBe("Source 2: Give an impedance or a current.");
  });

  it("keeps the message as it is when the issue has no path", () => {
    expect(describeValidationIssue(issue([], { code: "custom", message: "Review the inputs." }))).toBe(
      "Review the inputs.",
    );
  });

  it.each<[string, Partial<ValidationIssueLike>]>([
    ["type instead of origin", { code: "too_small", type: "string", minimum: 1 }],
    ["received undefined", { code: "invalid_type", expected: "string", received: "undefined" }],
  ])("understands the zod 3 shape: %s", (_name, rest) => {
    expect(describeValidationIssue(issue(["sources", 0, "name"], rest), labels)).toBe(
      "Source 1 — Name is required.",
    );
  });

  it("prints a bigint bound", () => {
    const raw = issue(["utilization"], { code: "too_small", origin: "bigint", minimum: 5n });
    expect(describeValidationIssue(raw, labels)).toBe("Utilization must be at least 5.");
  });
});
