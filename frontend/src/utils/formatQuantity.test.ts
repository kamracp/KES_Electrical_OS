import { describe, expect, it } from "vitest";

import { EMPTY_QUANTITY, formatQuantity, roundToSignificantFigures } from "./formatQuantity";

describe("roundToSignificantFigures", () => {
  it.each([
    ["35.219668322", "35.22"],
    ["84.583705423", "84.58"],
    ["0.880512", "0.8805"],
    ["123456", "123500"],
    ["-0.000123456", "-0.0001235"],
    ["1.0005", "1.001"],
    ["1.00049", "1.000"],
  ])("rounds %s half-up to %s", (exact, expected) => {
    expect(roundToSignificantFigures(exact)).toBe(expected);
  });

  it.each(["150", "0.8805", "8.149", "0.00709", "5"])(
    "leaves %s unchanged because it has four figures or fewer",
    (exact) => {
      expect(roundToSignificantFigures(exact)).toBe(exact);
    },
  );

  it.each([
    ["9.9996", "10.00"],
    ["0.99996", "1.000"],
    ["999.96", "1000"],
    ["999960", "1000000"],
  ])("carries %s into %s", (exact, expected) => {
    expect(roundToSignificantFigures(exact)).toBe(expected);
  });

  it.each(["0", "0.000"])("shows %s as zero", (exact) => {
    expect(roundToSignificantFigures(exact)).toBe("0");
  });

  it.each(["1E-7", "abc"])("returns null for %s because it is not a plain decimal", (text) => {
    expect(roundToSignificantFigures(text)).toBeNull();
  });
});

describe("formatQuantity", () => {
  it("appends the unit to the rounded and to the exact value", () => {
    expect(formatQuantity("35.219668322", "kA")).toEqual({
      display: "35.22 kA",
      exact: "35.219668322 kA",
    });
  });

  it("formats a ratio without a unit", () => {
    expect(formatQuantity("0.880512")).toEqual({ display: "0.8805", exact: "0.880512" });
  });

  it.each([null, undefined, ""])("returns the empty marker for %s", (value) => {
    expect(formatQuantity(value, "kA")).toEqual({ display: EMPTY_QUANTITY, exact: null });
  });

  it("shows a non-plain decimal exactly as the engine sent it", () => {
    expect(formatQuantity("1E-7", "kA")).toEqual({ display: "1E-7 kA", exact: "1E-7 kA" });
  });
});
