import type { CableSizingRequest } from "../services/cable";
import { CableSizingForm } from "../components/CableSizingForm";
import { CableSizingResultPanel } from "../components/CableSizingResultPanel";
import { CableWarningPanel } from "../components/CableWarningPanel";
import { useCableSizing } from "../hooks/useCableSizing";

function describeError(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return "The cable sizing calculation could not be completed.";
}

export function CableSizingPage() {
  const { calculate, reset, result, error, isPending, isError } = useCableSizing();

  // Errors are surfaced through the hook state below, not thrown into the form.
  async function handleSubmit(payload: CableSizingRequest): Promise<void> {
    try {
      await calculate(payload);
    } catch {
      // Intentionally empty: isError / error already describe the failure.
    }
  }

  return (
    <main>
      <header>
        <p>EOS-06 · Cable Sizing</p>
        <h1>Cable Sizing</h1>
        <p>
          Size LV power cables for ampacity, voltage drop, and short-circuit withstand using the
          validated KES Electrical OS calculation service.
        </p>
      </header>

      <section aria-labelledby="cable-sizing-inputs-heading">
        <h2 id="cable-sizing-inputs-heading">Inputs</h2>
        <CableSizingForm disabled={isPending} onSubmit={handleSubmit} />
      </section>

      <section aria-labelledby="cable-sizing-results-heading">
        <h2 id="cable-sizing-results-heading">Results</h2>

        {isPending ? (
          <p role="status" data-calculation-state="pending">
            Calculating cable size…
          </p>
        ) : null}

        {isError ? (
          <p role="alert" data-calculation-state="error">
            {describeError(error)}
          </p>
        ) : null}

        {result ? (
          <div data-calculation-state="success">
            <CableSizingResultPanel result={result} />
            <CableWarningPanel warnings={result.warnings} />
            <p>
              <button type="button" onClick={reset}>
                Clear results
              </button>
            </p>
          </div>
        ) : null}

        {!isPending && !isError && !result ? (
          <p data-calculation-state="idle">
            Submit the inputs above to run a cable sizing design check.
          </p>
        ) : null}
      </section>

      <section aria-labelledby="cable-sizing-review-heading">
        <h2 id="cable-sizing-review-heading">Engineering review required</h2>
        <p>
          Calculation results are engineering design checks, not a statutory compliance
          declaration. Confirm the governing project basis, the verified edition of the applicable
          standard, installation assumptions, and protective device coordination before approval
          or issue.
        </p>
      </section>
    </main>
  );
}

export default CableSizingPage;
