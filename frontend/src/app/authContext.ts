import { createContext, useContext } from "react";

import type { Session } from "../services/auth";

// Who is signed in, shared with every component through React context (EOS-01 a).
//
// The state is a closed set on purpose: a page is shown only for "signed-in". "loading" and
// "error" never count as signed in, so a slow or failed session check cannot reveal a page.

export type AuthState =
  | { status: "loading" }
  | { status: "signed-out" }
  | { status: "signed-in"; session: Session }
  | { status: "error"; message: string };

export type AuthContextValue = {
  state: AuthState;
  /** Sign in; rejects with the server's message when the credentials are refused. */
  signIn: (email: string, password: string) => Promise<Session>;
  /** Close the session on the server; rejects (and stays signed in) when that fails. */
  signOut: () => Promise<void>;
  /** Ask the server again who is signed in (after a password change, a 401, or a retry). */
  refresh: () => Promise<void>;
};

/** react-query key of the session; every other cached query belongs to the signed-in user. */
export const SESSION_QUERY_KEY = ["auth", "session"] as const;

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);

  if (value === null) {
    throw new Error("useAuth must be used inside <AuthProvider>.");
  }

  return value;
}
