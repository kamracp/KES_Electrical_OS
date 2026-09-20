import type { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router-dom";

import "../styles/auth.css";
import { useAuth } from "./authContext";

// Route guards (EOS-01 a). The server refuses every protected API call on its own; these
// guards only decide which screen the browser shows, so a page never flashes before sign-in.

export const LOGIN_PATH = "/login";
export const CHANGE_PASSWORD_PATH = "/change-password";
export const USERS_PATH = "/users";

type ReturnState = { from: string };

/** Only a path inside this application is accepted as the place to return to after sign-in. */
function safeReturnPath(state: unknown): string {
  if (typeof state !== "object" || state === null || !("from" in state)) {
    return "/";
  }

  const from = (state as { from: unknown }).from;

  if (typeof from !== "string" || !from.startsWith("/") || /^\/[/\\]/.test(from)) {
    return "/";
  }
  if (from === LOGIN_PATH || from.startsWith(`${LOGIN_PATH}?`)) {
    return "/";
  }

  return from;
}

function SessionCheckPending() {
  return (
    <p role="status" data-auth-state="loading">
      Checking your session…
    </p>
  );
}

function SessionCheckFailed({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" data-auth-state="error">
      <p>{message}</p>
      <p>No page is shown until the session has been checked.</p>
      <button type="button" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}

type RequireAuthProps = PropsWithChildren<{
  /** Set on the change-password route only: it must stay reachable while a change is due. */
  allowPasswordChangePending?: boolean;
}>;

/** Shows its children to a signed-in user; everybody else is sent to the sign-in page. */
export function RequireAuth({ children, allowPasswordChangePending = false }: RequireAuthProps) {
  const { state, refresh } = useAuth();
  const location = useLocation();

  if (state.status === "loading") {
    return <SessionCheckPending />;
  }
  if (state.status === "error") {
    return <SessionCheckFailed message={state.message} onRetry={() => void refresh()} />;
  }
  if (state.status === "signed-out") {
    const returnState: ReturnState = {
      from: `${location.pathname}${location.search}${location.hash}`,
    };
    return <Navigate to={LOGIN_PATH} replace state={returnState} />;
  }
  if (state.session.user.must_change_password && !allowPasswordChangePending) {
    // The API answers 403 to everything until a first or reset password has been changed.
    return <Navigate to={CHANGE_PASSWORD_PATH} replace />;
  }

  return <>{children}</>;
}

/** The sign-in page: a user who is already signed in is sent on to where they were going. */
export function SignedOutOnly({ children }: PropsWithChildren) {
  const { state, refresh } = useAuth();
  const location = useLocation();

  if (state.status === "loading") {
    return <SessionCheckPending />;
  }
  if (state.status === "error") {
    return <SessionCheckFailed message={state.message} onRetry={() => void refresh()} />;
  }
  if (state.status === "signed-in") {
    const target = state.session.user.must_change_password
      ? CHANGE_PASSWORD_PATH
      : safeReturnPath(location.state);
    return <Navigate to={target} replace />;
  }

  return <>{children}</>;
}
