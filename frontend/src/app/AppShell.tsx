import { Link, NavLink, Outlet } from "react-router-dom";

import "../styles/shell.css";
import { BackButton } from "../components/BackButton";
import { MODULES, MODULE_STATUS_LABELS } from "./modules";

// The sidebar renders every module from the registry so the product structure is
// always visible; only modules with a working page are links.
export function AppShell() {
  return (
    <div data-shell>
      <aside aria-label="Modules">
        <Link to="/" data-brand>
          KES Electrical OS
          <small>LV electrical design checks</small>
        </Link>
        <nav aria-label="Primary">
          <ul>
            <li>
              <NavLink to="/" end>
                <span data-module-code-label>Home</span>
                <span>Overview</span>
              </NavLink>
            </li>
            {MODULES.map((module) => {
              const statusLabel = MODULE_STATUS_LABELS[module.status];
              const body = (
                <>
                  <span data-module-code-label>{module.code}</span>
                  <span>{module.name}</span>
                  <span data-module-status={statusLabel}>{statusLabel}</span>
                </>
              );
              return (
                <li key={module.code} data-module-code={module.code}>
                  {module.route ? (
                    <NavLink to={module.route}>{body}</NavLink>
                  ) : (
                    <span aria-disabled="true">{body}</span>
                  )}
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>

      <div data-shell-body>
        <header aria-label="Product">
          <BackButton />
          <span>Engineering design checks against referenced standard data</span>
          <span>Kamra Engineering Solutions</span>
        </header>

        <div data-shell-content>
          <Outlet />
        </div>

        <footer aria-label="Engineering basis">
          <p>
            Results are engineering design checks, not a statutory compliance certification, and
            require independent engineering review before use.
          </p>
          <p>
            Reference data status is shown with every result: Verified, Unverified or Unresolved.
            Product data is identified by class, specification and rating only; no manufacturer
            is named.
          </p>
        </footer>
      </div>
    </div>
  );
}
