export function FaultStudyPage() {
  return (
    <main>
      <header>
        <p>EOS-04 · Short-Circuit &amp; Earth-Fault</p>
        <h1>Fault Study</h1>
        <p>
          Build and review prospective short-circuit and earth-fault studies
          using the validated KES Electrical OS calculation service.
        </p>
      </header>

      <section aria-labelledby="fault-study-basis-heading">
        <h2 id="fault-study-basis-heading">Engineering basis</h2>
        <p>
          Use verified network topology, source data, sequence impedances, and
          operating-state assumptions before issuing engineering conclusions.
        </p>
        <ul>
          <li>Maximum and minimum prospective fault calculation cases.</li>
          <li>
            Three-phase, phase-to-phase, phase-to-phase-to-earth, and
            single-phase-to-earth fault configurations.
          </li>
          <li>
            Exact decimal engineering values preserved through the frontend API
            boundary.
          </li>
        </ul>
      </section>

      <section aria-labelledby="fault-study-review-heading">
        <h2 id="fault-study-review-heading">Engineering review required</h2>
        <p>
          Calculation results are engineering evidence, not an automatic
          compliance declaration. Confirm the governing project basis,
          applicable standard edition, assumptions, and protection duties
          before approval or issue.
        </p>
      </section>
    </main>
  );
}
