import { Link } from "react-router-dom";

import { ApiHealthStatus } from "./components/ApiHealthStatus";

type ModuleStatus = "Live" | "Placeholder" | "Backend only" | "Planned";

type ModuleCard = {
  code: string;
  title: string;
  summary: string;
  status: ModuleStatus;
  to?: string;
};

// Status mirrors docs/project-status.md; a card gets a link only when its page works.
const MODULES: ModuleCard[] = [
  {
    code: "EOS-06",
    title: "Cable Sizing",
    summary:
      "LV cable selection with ampacity, voltage-drop and short-circuit checks, derating warnings and reference verification status.",
    status: "Live",
    to: "/cable-sizing",
  },
  {
    code: "EOS-04",
    title: "Fault Study",
    summary: "Short-circuit study workspace. Engine complete; the page is a placeholder until it is wired.",
    status: "Live",
    to: "/fault-study",
  },
  {
    code: "EOS-02",
    title: "Load and Demand",
    summary: "Connected load, diversity and maximum demand runs.",
    status: "Backend only",
  },
  {
    code: "EOS-03",
    title: "Sources",
    summary: "Transformer, generator, UPS and PV sizing.",
    status: "Backend only",
  },
  {
    code: "EOS-07",
    title: "Panels and Switchgear",
    summary: "LT PCC and HT panel foundations.",
    status: "Backend only",
  },
  {
    code: "EOS-08",
    title: "Earthing and Lightning",
    summary: "Earthing design and lightning protection.",
    status: "Planned",
  },
];

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
          Standards-governed calculation, verification, review, and engineering deliverables
          workspace. Each study is designed under a selectable jurisdiction profile; engine physics
          is universal, references and conventions follow the profile.
        </p>
      </section>

      <section aria-labelledby="modules-heading">
        <h2 id="modules-heading">Modules</h2>
        <ul>
          {MODULES.map((module) => (
            <li key={module.code} data-module-code={module.code} data-module-status={module.status}>
              <h3>
                {module.code} · {module.title}
              </h3>
              <p>{module.summary}</p>
              <p>
                <small>{module.status}</small>
              </p>
              {module.to ? <Link to={module.to}>Open {module.title}</Link> : null}
            </li>
          ))}
        </ul>
      </section>

      <ApiHealthStatus />
    </main>
  );
}
