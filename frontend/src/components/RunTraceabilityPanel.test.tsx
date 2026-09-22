// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CalculationRunSummary } from "../services/cable";
import { RunTraceabilityPanel } from "./RunTraceabilityPanel";

const run: CalculationRunSummary = {
  id: "48a782d0-4331-4aa2-bcd0-f24f5016334a",
  module_code: "EOS-06",
  project_revision_id: null,
  project: null,
  calculation_type: "CABLE_SIZING",
  calculation_key: "CBL-001",
  revision_number: 2,
  run_status: "COMPLETED",
  approval_status: "NOT_SUBMITTED",
  engine_version: "cable-engine 0.1.0",
  design_check_status: "REVIEW_REQUIRED",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  content_hash: "e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e280",
  calculated_by: "C. Kamra",
  calculated_at: "2026-09-17T12:34:56+00:00",
  created_at: "2026-09-17T12:34:56+00:00",
  is_immutable: false,
  supersedes_run_id: null,
  notes: null,
};

describe("RunTraceabilityPanel", () => {
  afterEach(cleanup);

  it("renders the stored run identity, engine, references, hash and approval state", () => {
    render(<RunTraceabilityPanel run={run} />);

    const panel = document.querySelector('[data-run-id="48a782d0-4331-4aa2-bcd0-f24f5016334a"]');
    expect(panel).not.toBeNull();
    expect(panel?.querySelector('[data-field="revision"]')?.textContent).toBe("2");
    expect(panel?.querySelector('[data-field="engine-version"]')?.textContent).toBe(
      "cable-engine 0.1.0",
    );
    expect(panel?.querySelector('[data-field="content-hash"]')?.textContent).toBe(
      run.content_hash,
    );
    expect(panel?.querySelector('[data-field="calculated-at"]')?.textContent).toBe(
      "2026-09-17 12:34:56 UTC by C. Kamra",
    );
    expect(panel?.querySelector('[data-field="approval-status"]')?.textContent).toBe(
      "Not submitted for review",
    );
    expect(screen.queryByRole("button", { name: "Download run JSON" })).toBeNull();
  });

  it("offers the export only when a handler is supplied and calls it", () => {
    const onExport = vi.fn();
    render(<RunTraceabilityPanel run={run} onExport={onExport} />);

    fireEvent.click(screen.getByRole("button", { name: "Download run JSON" }));

    expect(onExport).toHaveBeenCalledTimes(1);
  });
});
