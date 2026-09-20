import { describe, expect, it } from "vitest";

import { describePasswordProblem } from "./passwordPolicy";

const EMAIL = "engineer@example.com";

describe("describePasswordProblem", () => {
  it.each([
    ["", "First password is required."],
    ["too short", "First password must have at least 12 characters."],
    ["x".repeat(129), "First password must have at most 128 characters."],
    [" ".repeat(12), "First password must not be blank."],
    ["Engineer@Example.com", "First password must not be the e-mail address."],
  ])("refuses %j", (password, message) => {
    expect(describePasswordProblem(password, EMAIL, "First password")).toBe(message);
  });

  it.each(["exactly12chr", "four words with spaces", "x".repeat(128)])("accepts %j", (password) => {
    expect(describePasswordProblem(password, EMAIL, "First password")).toBeNull();
  });

  it("does not compare with an e-mail that has not been entered yet", () => {
    expect(describePasswordProblem("four words with spaces", "  ", "First password")).toBeNull();
  });
});
