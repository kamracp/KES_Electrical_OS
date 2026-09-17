import { describe, expect, it } from "vitest";

import { MODULES, MODULE_STATUS_LABELS, getModule, liveModules } from "./modules";

describe("module registry", () => {
  it("lists all fifteen modules in EOS order", () => {
    expect(MODULES).toHaveLength(15);
    MODULES.forEach((module, index) => {
      const expectedCode = `EOS-${String(index + 1).padStart(2, "0")}`;
      expect(module.code).toBe(expectedCode);
    });
  });

  it("gives a route to live modules only", () => {
    for (const module of MODULES) {
      if (module.status === "LIVE") {
        expect(module.route).not.toBeNull();
      } else {
        expect(module.route).toBeNull();
      }
    }
  });

  it("has a label for every status", () => {
    for (const module of MODULES) {
      expect(MODULE_STATUS_LABELS[module.status]).toBeTruthy();
    }
  });

  it("exposes lookups", () => {
    expect(getModule("EOS-06")?.route).toBe("/cable-sizing");
    expect(getModule("EOS-99")).toBeUndefined();
    expect(liveModules().map((module) => module.code)).toEqual(["EOS-04", "EOS-06"]);
  });
});
