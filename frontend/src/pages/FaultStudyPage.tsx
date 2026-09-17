import type { ShortCircuitStudyRequest } from "../services/fault";
import { FaultStudyForm } from "../components/FaultStudyForm";
import { FaultStudyResultPanel } from "../components/FaultStudyResultPanel";
import { FaultWarningPanel } from "../components/FaultWarningPanel";
import { useFaultStudy } from "../hooks/useFaultStudy";

function describeError(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return "The short-circuit study could not be completed.";
}

export function FaultStudyPage() {
  const { calculate, reset, result, error, isPending, isError } = useFaultStudy();

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

      <section aria-labelledby="fault-study-inputs-heading">
        <h2 id="fault-study-inputs-heading">Inputs</h2>
        <FaultStudyForm disabled={isPending} onSubmit={handleSubmit} />
      </section>

      <section aria-labelledby="fault-study-results-heading">
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
            <FaultStudyResultPanel result={result} />
            <FaultWarningPanel warnings={result.warnings} />
            <p>
              <button type="button" onClick={reset}>
                Clear results
              </button>
            </p>
          </div>
        ) : null}

        {!isPending && !isError && !result ? (
          <p data-calculation-state="idle">
            Submit the inputs above to run a short-circuit study.
          </p>
        ) : null}
      </section>

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
