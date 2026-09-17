import { Link } from "react-router-dom";

import "./styles/home.css";
import { MODULES, MODULE_STATUS_LABELS } from "./app/modules";
import { ApiHealthStatus } from "./components/ApiHealthStatus";

// The home page renders every module from the registry; a card gets a link only
// when its page works, and its status badge mirrors docs/project-status.md.
export function App() {
  return (
    <main>
      <header>
        <p>Kamra Engineering Solutions</p>
        <h1>KES Electrical OS</h1>
      </header>

      <section aria-labelledby="workspace-heading">
        <h2 id="workspace-heading">Electrical Engineering Workspace</h2>
        <p data-home-intro>
          Standards-governed calculation, verification, review and engineering deliverables. Each
          study runs under a selectable jurisdiction profile: engine physics is universal, references
          and conventions follow the profile.
        </p>
      </section>

      <section aria-labelledby="modules-heading">
        <h2 id="modules-heading">Modules</h2>
        <ul data-module-grid>
          {MODULES.map((module) => {
            const statusLabel = MODULE_STATUS_LABELS[module.status];
            return (
              <li key={module.code} data-module-code={module.code} data-module-status={module.status}>
                <h3>
                  <span>{module.name}</span>
                  <span data-module-code-label>{module.code}</span>
                </h3>
                <p>{module.summary}</p>
                <span data-module-status={statusLabel}>{statusLabel}</span>
                {module.route ? <Link to={module.route}>Open {module.name}</Link> : null}
              </li>
            );
          })}
        </ul>
      </section>

      <ApiHealthStatus />
    </main>
  );
}
