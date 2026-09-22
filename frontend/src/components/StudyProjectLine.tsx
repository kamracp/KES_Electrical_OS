import { Link } from "react-router-dom";

import { useProject } from "../app/projectContext";

// Which project a study on this page will be saved in (Master Prompt v2.1 section 19,
// "Project and scenario identity"). The project is chosen in the shell topbar; this line only
// says what that choice means for the next run, before it is calculated.

const REVISION_STATUS_LABELS: Record<string, string> = {
  OPEN: "Open",
  ISSUED: "Issued",
  SUPERSEDED: "Superseded",
};

export function StudyProjectLine() {
  const { state } = useProject();

  if (state.status === "none" || state.status === "loading") {
    return (
      <p data-study-project data-study-project-state="none">
        No project — this run will be unassigned. <Link to="/projects">Projects</Link>
      </p>
    );
  }

  const { project, revision } = state;
  const status = REVISION_STATUS_LABELS[revision.status] ?? revision.status;

  return (
    <p data-study-project data-study-project-state={state.status}>
      Project {project.code} — {project.name} · {revision.label} ({status})
      {state.status === "read-only" ? (
        <>
          {". "}
          <span data-study-project-hint>
            No open revision — this run will not be linked to this project.
          </span>{" "}
          <Link to="/projects">Projects</Link>
        </>
      ) : null}
    </p>
  );
}
