import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import "../styles/auth.css";
import { useAuth } from "../app/authContext";
import { changePassword } from "../services/auth";
import { ApiError } from "../services/http";
import { PASSWORD_MIN_LENGTH, describePasswordProblem } from "../utils/passwordPolicy";

// Change the own password (EOS-01 a). A user with a first or reset password is held here by
// the route guard until the change is done, because the API refuses everything else (403).
//
// The checks below only save a round trip; the server applies the password rule again and
// stays the authority. Passwords are never trimmed and never stored by the browser code.

const UNREACHABLE = "The server could not be reached. Check the connection and try again.";

type Draft = { current: string; next: string; repeat: string };

const EMPTY_DRAFT: Draft = { current: "", next: "", repeat: "" };

function checkDraft(draft: Draft, email: string): string | null {
  if (draft.current === "") {
    return "Current password is required.";
  }

  const problem = describePasswordProblem(draft.next, email, "New password");

  if (problem !== null) {
    return problem;
  }
  if (draft.next === draft.current) {
    return "New password must differ from the current password.";
  }
  if (draft.repeat !== draft.next) {
    return "The two new passwords do not match.";
  }
  return null;
}

function describeFailure(caught: unknown): string {
  return caught instanceof ApiError ? caught.message : UNREACHABLE;
}

export function ChangePasswordPage() {
  const { state, refresh, signOut } = useAuth();
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [changed, setChanged] = useState(false);

  if (state.status !== "signed-in") {
    return null;
  }

  const { user } = state.session;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    const problem = checkDraft(draft, user.email);

    if (problem !== null) {
      setError(problem);
      return;
    }

    setError(null);
    setPending(true);

    try {
      await changePassword(draft.current, draft.next);
      setChanged(true);
      // The session now says "no change due", which opens the rest of the application.
      await refresh();
    } catch (caught) {
      setError(describeFailure(caught));
    } finally {
      setDraft(EMPTY_DRAFT);
      setPending(false);
    }
  }

  async function leave(): Promise<void> {
    setError(null);

    try {
      await signOut();
    } catch (caught) {
      setError(describeFailure(caught));
    }
  }

  return (
    <main data-auth-page>
      <header>
        <p>Kamra Engineering Solutions</p>
        <h1>KES Electrical OS</h1>
      </header>

      <section aria-labelledby="change-password-heading" data-auth-card>
        <h2 id="change-password-heading">Change your password</h2>

        {changed ? (
          <>
            <p role="status">
              Your password has been changed. Your sessions on other devices were closed.
            </p>
            <p data-auth-actions>
              <Link to="/">Continue to Home</Link>
            </p>
          </>
        ) : (
          <>
            {user.must_change_password ? (
              <p>A first or reset password must be changed before any study can be opened.</p>
            ) : null}

            <form onSubmit={(event) => void submit(event)} noValidate>
              <label>
                Current password
                <input
                  type="password"
                  name="current-password"
                  autoComplete="current-password"
                  value={draft.current}
                  onChange={(event) => setDraft({ ...draft, current: event.target.value })}
                />
              </label>
              <label>
                New password
                <input
                  type="password"
                  name="new-password"
                  autoComplete="new-password"
                  value={draft.next}
                  onChange={(event) => setDraft({ ...draft, next: event.target.value })}
                />
              </label>
              <label>
                Repeat new password
                <input
                  type="password"
                  name="repeat-new-password"
                  autoComplete="new-password"
                  value={draft.repeat}
                  onChange={(event) => setDraft({ ...draft, repeat: event.target.value })}
                />
              </label>

              {error !== null ? <p role="alert">{error}</p> : null}

              <button type="submit" disabled={pending}>
                {pending ? "Changing…" : "Change password"}
              </button>
            </form>

            <p data-auth-note>
              At least {PASSWORD_MIN_LENGTH} characters. Length is what counts: a passphrase of
              several words with spaces is welcome, and no special characters are demanded.
            </p>

            <p data-auth-actions>
              <span>Signed in as {user.email}</span>
              {user.must_change_password ? null : <Link to="/">Back to Home</Link>}
              <button type="button" onClick={() => void leave()}>
                Sign out
              </button>
            </p>
          </>
        )}
      </section>
    </main>
  );
}
