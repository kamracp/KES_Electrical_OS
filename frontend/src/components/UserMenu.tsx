import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../app/authContext";
import { ROLE_LABELS } from "../app/roles";
import { CHANGE_PASSWORD_PATH } from "../app/routeGuards";
import { ApiError } from "../services/http";

// Who is signed in, shown once in the shell topbar (EOS-01 a), with the two account actions:
// change the own password and sign out. Signing out is done by the server; when it succeeds
// the session state turns "signed-out" and the route guard shows the sign-in page.

const UNREACHABLE = "Sign-out failed: the server could not be reached.";

export function UserMenu() {
  const { state, signOut } = useAuth();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (state.status !== "signed-in") {
    return null;
  }

  const { user, organization, role } = state.session;

  async function leave(): Promise<void> {
    setError(null);
    setPending(true);

    try {
      await signOut();
    } catch (caught) {
      // Still signed in: only the server can end the session and remove the cookie.
      setError(caught instanceof ApiError ? caught.message : UNREACHABLE);
      setPending(false);
    }
  }

  return (
    <div data-shell-user>
      <span data-shell-user-name title={user.email}>
        {user.full_name}
      </span>
      <span data-shell-user-role>
        {ROLE_LABELS[role]} · {organization.name}
      </span>
      <Link to={CHANGE_PASSWORD_PATH}>Change password</Link>
      <button type="button" onClick={() => void leave()} disabled={pending}>
        {pending ? "Signing out…" : "Sign out"}
      </button>
      {error !== null ? <span role="alert">{error}</span> : null}
    </div>
  );
}
