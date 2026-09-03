import { ApiHealthStatus } from "./components/ApiHealthStatus";

export function App() {
  return (
    <main>
      <header>
        <p>Kamra Engineering Solutions</p>
        <h1>KES Electrical OS</h1>
      </header>

      <section aria-labelledby="workspace-heading">
        <h2 id="workspace-heading">Electrical Engineering Workspace</h2>
        <p>
          Standards-governed calculation, verification, review, and engineering
          deliverables workspace.
        </p>
      </section>

      <ApiHealthStatus />
    </main>
  );
}
