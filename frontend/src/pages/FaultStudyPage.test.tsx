// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { FaultStudyPage } from "./FaultStudyPage";

afterEach(() => {
  cleanup();
});

describe("FaultStudyPage", () => {
  it("renders the EOS-04 workspace and engineering basis", () => {
    render(<FaultStudyPage />);

    expect(screen.getByRole("heading", { name: "Fault Study", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("EOS-04 · Short-Circuit & Earth-Fault")).toBeInTheDocument();

    const basis = screen.getByRole("region", { name: "Engineering basis" });
    expect(
      within(basis).getByText("Maximum and minimum prospective fault calculation cases."),
    ).toBeInTheDocument();
    expect(
      within(
        basis,
      ).getByText(/Exact decimal engineering values preserved/),
    ).toBeInTheDocument();
  });

  it("keeps the engineering review warning visible", () => {
    render(<FaultStudyPage />);

    const review = screen.getByRole("region", { name: "Engineering review required" });
    expect(within(review).getByText(/not an automatic compliance declaration/i)).toBeInTheDocument();
    expect(within(review).getByText(/applicable standard edition/i)).toBeInTheDocument();
  });
});
