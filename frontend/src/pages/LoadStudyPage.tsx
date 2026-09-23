import "../styles/study.css";

import type { LoadRunCreateRequest } from "../services/loadDemand";
import { downloadRunJson } from "../services/runExport";
import { LoadResultPanel } from "../components/LoadResultPanel";
import { LoadResultSummary } from "../components/LoadResultSummary";
import { LoadStudyForm } from "../components/LoadStudyForm";
import { LoadWarningPanel } from "../components/LoadWarningPanel";
import { RunTraceabilityPanel } from "../components/RunTraceabilityPanel";
import { StudyProjectLine } from "../components/StudyProjectLine";
import { useLoadStudy } from "../hooks/useLoadStudy";

function describeError(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return "The load and demand study could not be completed.";
}

// Study-page layout (Master Prompt v2.1 section 19): collapsible inputs beside
// a result-first column - summary, warnings, traceability, then detail tables.
export function LoadStudyPage() {
  const { calculate, reset, result, run, error, isPending, isError } = useLoadStudy();

  // Errors are surfaced through the hook state below, not thrown into the form.
  async function handleSubmit(payload: LoadRunCreateRequest): Promise<void> {
    try {
      await calculate(payload);
    } catch {
      // Intentionally empty: isError / error already describe the failure.
    }
  }

  return (
    <main data-load-study-page>
      <header>
        <p>EOS-02 · Load &amp; Demand</p>
        <h1>Load and demand</h1>
        <p>
          Build a load schedule and review its connected load, maximum demand and design
          current using the validated KES Electrical OS calculation service.
        </p>
      </header>

      <div data-study-layout>
        <section aria-labelledby="load-study-inputs-heading">
          <details open data-study-inputs>
            <summary>
              <h2 id="load-study-inputs-heading">Inputs</h2>
            </summary>
            <StudyProjectLine />
            <LoadStudyForm disabled={isPending} onSubmit={handleSubmit} />
          </details>
        </section>

        <section aria-labelledby="load-study-results-heading" data-study-results>
          <h2 id="load-study-results-heading">Results</h2>

          {isPending ? (
            <p role="status" data-calculation-state="pending">
              Calculating the load schedule…
            </p>
          ) : null}

          {isError ? (
            <p role="alert" data-calculation-state="error">
              {describeError(error)}
            </p>
          ) : null}

          {result ? (
            <div data-calculation-state="success">
              <LoadResultSummary result={result} />
              <LoadWarningPanel warnings={result.warnings} />
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
              <LoadResultPanel result={result} />
              <p>
                <button type="button" onClick={reset}>
                  Clear results
                </button>
              </p>
            </div>
          ) : null}

          {!isPending && !isError && !result ? (
            <p data-calculation-state="idle">
              Submit the inputs to calculate a load schedule.
            </p>
          ) : null}
        </section>
      </div>

      <section aria-labelledby="load-study-review-heading">
        <h2 id="load-study-review-heading">Engineering review required</h2>
        <p>
          Calculation results are engineering evidence, not an automatic compliance
          declaration. Confirm the governing project basis, the connected load data and every
          diversity, utilization and coincidence factor before approval or issue.
        </p>
      </section>
    </main>
  );
}

export default LoadStudyPage;
