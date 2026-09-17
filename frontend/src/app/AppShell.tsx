import { NavLink, Outlet } from "react-router-dom";

type ModuleLink = {
  to: string;
  label: string;
  end?: boolean;
  code?: string;
  status?: "Live" | "Placeholder" | "Planned";
};

// Navigation reflects what is actually deployed; a route without a working page is labelled.
const MODULE_LINKS: ModuleLink[] = [
  { to: "/", label: "Home", end: true },
  { to: "/cable-sizing", label: "Cable Sizing", code: "EOS-06", status: "Live" },
  { to: "/fault-study", label: "Fault Study", code: "EOS-04", status: "Placeholder" },
];

export function AppShell() {
  return (
    <>
      <nav aria-label="Primary">
        <ul>
          {MODULE_LINKS.map((link) => (
            <li key={link.to} data-module-code={link.code}>
              <NavLink to={link.to} end={link.end}>
                {link.label}
              </NavLink>
              {link.code ? (
                <small data-module-status={link.status}>
                  {" "}
                  {link.code} · {link.status}
                </small>
              ) : null}
            </li>
          ))}
        </ul>
      </nav>

      <Outlet />

      <footer aria-label="Engineering basis">
        <p>
          Results are engineering design checks against referenced standard data. They are not a
          statutory compliance certification and require independent engineering review before use.
        </p>
        <p>
          Reference data status shown with every result: Verified, Unverified, or Unresolved
          (reference data pending). Product data is identified by class, specification and rating
          only; no manufacturer is named.
        </p>
        <p>Kamra Engineering Solutions · KES Electrical OS</p>
      </footer>
    </>
  );
}
