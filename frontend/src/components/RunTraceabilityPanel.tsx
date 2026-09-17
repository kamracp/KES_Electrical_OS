import type { CalculationRunSummary } from "../services/cable";

type RunTraceabilityPanelProps = {
  run: CalculationRunSummary;
  onExport?: () => void;
};

const APPROVAL_LABELS: Record<string, string> = {
  NOT_SUBMITTED: "Not submitted for review",
  PENDING: "Pending review",
  APPROVED: "Approved",
  REJECTED: "Rejected",
};

// Traceability record of a persisted run (Master Prompt v2.1 section 19):
// every value comes from the stored run, never from the client-side result.
export function RunTraceabilityPanel({ run, onExport }: RunTraceabilityPanelProps) {
  const calculatedAt = new Date(run.calculated_at);
  const calculatedLabel = Number.isNaN(calculatedAt.getTime())
    ? run.calculated_at
    : calculatedAt.toISOString().replace("T", " ").slice(0, 19) + " UTC";

  return (
    <section aria-label="Traceability" data-run-id={run.id}>
      <h3>Traceability</h3>
      <dl>
        <dt>Run ID</dt>
        <dd data-field="run-id">{run.id}</dd>
        <dt>Revision</dt>
        <dd data-field="revision">{run.revision_number}</dd>
        <dt>Engine version</dt>
        <dd data-field="engine-version">{run.engine_version}</dd>
        <dt>Jurisdiction profile</dt>
        <dd data-field="profile">{run.jurisdiction_profile}</dd>
        <dt>Reference status</dt>
        <dd data-field="reference-status">{run.reference_verification_status}</dd>
        <dt>Content hash (SHA-256)</dt>
        <dd data-field="content-hash">{run.content_hash}</dd>
        <dt>Calculated</dt>
        <dd data-field="calculated-at">
          {calculatedLabel}
          {run.calculated_by ? ` by ${run.calculated_by}` : ""}
        </dd>
        <dt>Approval state</dt>
        <dd data-field="approval-status">
          {APPROVAL_LABELS[run.approval_status] ?? run.approval_status}
          {run.is_immutable ? " (immutable)" : ""}
        </dd>
      </dl>
      {onExport ? (
        <p>
          <button type="button" onClick={onExport}>
            Download run JSON
          </button>
        </p>
      ) : null}
    </section>
  );
}
