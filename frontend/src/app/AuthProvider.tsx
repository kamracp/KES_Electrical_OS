import { useCallback, useMemo, type PropsWithChildren } from "react";
import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import {
  getSession,
  signIn as requestSignIn,
  signOut as requestSignOut,
  type Session,
} from "../services/auth";
import {
  AuthContext,
  SESSION_QUERY_KEY,
  type AuthContextValue,
  type AuthState,
} from "./authContext";

// Holds the session for the whole application (EOS-01 a).
//
// The browser cannot read the HttpOnly session cookie, so the only way to know who is signed
// in is to ask the server: GET /auth/me through getSession(). The answer is kept in the
// react-query cache under SESSION_QUERY_KEY; nothing is written to localStorage.

const SESSION_STALE_MS = 60_000;

/** Study data cached for one user must never be shown to the next user of the same browser. */
function dropUserData(queryClient: QueryClient): void {
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== SESSION_QUERY_KEY[0] });
  queryClient.getMutationCache().clear();
}

function describeFailure(error: unknown): string {
  return error instanceof Error && error.message !== ""
    ? error.message
    : "The session could not be checked.";
}

export function AuthProvider({ children }: PropsWithChildren) {
  const queryClient = useQueryClient();

  const sessionQuery = useQuery({
    queryKey: SESSION_QUERY_KEY,
    queryFn: ({ signal }) => getSession(signal),
    staleTime: SESSION_STALE_MS,
    // Coming back to the tab after the idle timeout must not leave a stale "signed in".
    refetchOnWindowFocus: true,
  });

  const { data, error, isError, isFetching } = sessionQuery;

  const state = useMemo<AuthState>(() => {
    // A known answer wins: a failed background re-check must not unmount a half-filled form.
    if (data !== undefined) {
      return data === null ? { status: "signed-out" } : { status: "signed-in", session: data };
    }
    if (isError && !isFetching) {
      return { status: "error", message: describeFailure(error) };
    }
    return { status: "loading" };
  }, [data, error, isError, isFetching]);

  const signIn = useCallback(
    async (email: string, password: string): Promise<Session> => {
      const session = await requestSignIn(email, password);
      dropUserData(queryClient);
      queryClient.setQueryData(SESSION_QUERY_KEY, session);
      return session;
    },
    [queryClient],
  );

  const signOut = useCallback(async (): Promise<void> => {
    // Only the server can remove the cookie: if this call fails the user is still signed in.
    await requestSignOut();
    queryClient.setQueryData(SESSION_QUERY_KEY, null);
    dropUserData(queryClient);
  }, [queryClient]);

  const refresh = useCallback(async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({ state, signIn, signOut, refresh }),
    [state, signIn, signOut, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
