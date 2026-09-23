import "../styles/study.css";

import type { TransformerRunCreateRequest } from "../services/transformerSizing";
import { downloadRunJson } from "../services/runExport";
import { TransformerResultPanel } from "../components/TransformerResultPanel";
import { TransformerResultSummary } from "../components/TransformerResultSummary";
import { TransformerStudyForm } from "../components/TransformerStudyForm";
import { TransformerWarningPanel } from "../components/TransformerWarningPanel";
import { RunTraceabilityPanel } from "../components/RunTraceabilityPanel";
import { StudyProjectLine } from "../components/StudyProjectLine";
import { useTransformerSizing } from "../hooks/useTransformerSizing";

function describeError(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return "The transformer sizing study could not be completed.";
}

// Study-page layout (Master Prompt v2.1 section 19): collapsible inputs beside
// a result-first column - summary, warnings, traceability, then detail tables.
export function TransformerSizingPage() {
  const { calculate, reset, result, run, error, isPending, isError } = useTransformerSizing();

  // Errors are surfaced through the hook state below, not thrown into the form.
  async function handleSubmit(payload: TransformerRunCreateRequest): Promise<void> {
    try {
      await calculate(payload);
    } catch {
      // Intentionally empty: isError / error already describe the failure.
    }
  }

  return (
    <main data-transformer-sizing-page>
      <header>
        <p>EOS-03 · Transformer Sizing</p>
        <h1>Transformer sizing</h1>
        <p>
          Size a transformer against the demand, the design factors and the rating schedule
          of the project design basis, using the validated KES Electrical OS calculation
          service.
        </p>
      </header>

      <div data-study-layout>
        <section aria-labelledby="transformer-study-inputs-heading">
          <details open data-study-inputs>
            <summary>
              <h2 id="transformer-study-inputs-heading">Inputs</h2>
            </summary>
            <StudyProjectLine />
            <TransformerStudyForm disabled={isPending} onSubmit={handleSubmit} />
          </details>
        </section>

        <section aria-labelledby="transformer-study-results-heading" data-study-results>
          <h2 id="transformer-study-results-heading">Results</h2>

          {isPending ? (
            <p role="status" data-calculation-state="pending">
              Calculating the transformer size…
            </p>
          ) : null}

          {isError ? (
            <p role="alert" data-calculation-state="error">
              {describeError(error)}
            </p>
          ) : null}

          {result ? (
            <div data-calculation-state="success">
              <TransformerResultSummary result={result} />
              <TransformerWarningPanel warnings={result.warnings} />
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
              <TransformerResultPanel result={result} />
              <p>
                <button type="button" onClick={reset}>
                  Clear results
                </button>
              </p>
            </div>
          ) : null}

          {!isPending && !isError && !result ? (
            <p data-calculation-state="idle">
              Submit the inputs to size a transformer.
            </p>
          ) : null}
        </section>
      </div>

      <section aria-labelledby="transformer-study-review-heading">
        <h2 id="transformer-study-review-heading">Engineering review required</h2>
        <p>
          Calculation results are engineering evidence, not an automatic compliance
          declaration. Confirm the governing project basis, the demand data, the rating
          schedule and every growth, margin and derating factor before approval or issue.
        </p>
      </section>
    </main>
  );
}

export default TransformerSizingPage;
