import "../styles/study.css";

import type { ShortCircuitStudyRequest } from "../services/fault";
import { downloadRunJson } from "../services/runExport";
import { FaultResultSummary } from "../components/FaultResultSummary";
import { FaultStudyForm } from "../components/FaultStudyForm";
import { FaultStudyResultPanel } from "../components/FaultStudyResultPanel";
import { FaultWarningPanel } from "../components/FaultWarningPanel";
import { RunTraceabilityPanel } from "../components/RunTraceabilityPanel";
import { StudyProjectLine } from "../components/StudyProjectLine";
import { useFaultStudy } from "../hooks/useFaultStudy";

function describeError(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return "The short-circuit study could not be completed.";
}

// Study-page layout (Master Prompt v2.1 section 19): collapsible inputs beside
// a result-first column - summary, warnings, traceability, then detail tables.
export function FaultStudyPage() {
  const { calculate, reset, result, run, error, isPending, isError } = useFaultStudy();

  // Errors are surfaced through the hook state below, not thrown into the form.
  async function handleSubmit(payload: ShortCircuitStudyRequest): Promise<void> {
    try {
      await calculate(payload);
    } catch {
      // Intentionally empty: isError / error already describe the failure.
    }
  }

  return (
    <main>
      <header>
        <p>EOS-04 · Short-Circuit &amp; Earth-Fault</p>
        <h1>Fault Study</h1>
        <p>
          Build and review prospective short-circuit and earth-fault studies using the validated
          KES Electrical OS calculation service.
        </p>
      </header>

      <div data-study-layout>
        <section aria-labelledby="fault-study-inputs-heading">
          <details open data-study-inputs>
            <summary>
              <h2 id="fault-study-inputs-heading">Inputs</h2>
            </summary>
            <StudyProjectLine />
            <FaultStudyForm disabled={isPending} onSubmit={handleSubmit} />
          </details>
        </section>

        <section aria-labelledby="fault-study-results-heading" data-study-results>
          <h2 id="fault-study-results-heading">Results</h2>

          {isPending ? (
            <p role="status" data-calculation-state="pending">
              Calculating fault currents…
            </p>
          ) : null}

          {isError ? (
            <p role="alert" data-calculation-state="error">
              {describeError(error)}
            </p>
          ) : null}

          {result ? (
            <div data-calculation-state="success">
              <FaultResultSummary result={result} />
              <FaultWarningPanel warnings={result.warnings} />
              {run ? (
                <RunTraceabilityPanel
                  run={run}
                  onExport={() =>
                    downloadRunJson(
                      { run, result },
                      `${run.calculation_key}-rev${run.revision_number}.json`,
                    )
                  }
                />
              ) : null}
              <FaultStudyResultPanel result={result} />
              <p>
                <button type="button" onClick={reset}>
                  Clear results
                </button>
              </p>
            </div>
          ) : null}

          {!isPending && !isError && !result ? (
            <p data-calculation-state="idle">
              Submit the inputs to run a short-circuit study.
            </p>
          ) : null}
        </section>
      </div>

      <section aria-labelledby="fault-study-review-heading">
        <h2 id="fault-study-review-heading">Engineering review required</h2>
        <p>
          Calculation results are engineering evidence, not an automatic compliance declaration.
          Confirm the governing project basis, applicable standard edition, network data,
          assumptions and protection duties before approval or issue.
        </p>
      </section>
    </main>
  );
}

export default FaultStudyPage;
