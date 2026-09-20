import { useRef, useState, type FormEvent } from "react";

import "../styles/auth.css";
import { useAuth } from "../app/authContext";
import { ApiError } from "../services/http";

// The sign-in page (EOS-01 a). It stands outside the shell and is the only open page.
//
// The password lives in this component's state until the request has been sent and is
// cleared after a refused attempt; it is never written to localStorage or sessionStorage.
// After a successful sign-in this page does nothing more: the SignedOutOnly guard sees the
// new session and sends the user on to the page they came for.

const UNREACHABLE = "The server could not be reached. Check the connection and try again.";

export function LoginPage() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const passwordInput = useRef<HTMLInputElement>(null);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    const trimmedEmail = email.trim();

    if (trimmedEmail === "") {
      setError("E-mail is required.");
      return;
    }
    // No length check here: the rule for new passwords says nothing about an existing one.
    if (password === "") {
      setError("Password is required.");
      return;
    }

    setError(null);
    setPending(true);

    try {
      await signIn(trimmedEmail, password);
    } catch (caught) {
      // The server gives one message for an unknown e-mail, a wrong password and a lockout.
      setError(caught instanceof ApiError ? caught.message : UNREACHABLE);
      setPassword("");
      setPending(false);
      passwordInput.current?.focus();
    }
  }

  return (
    <main data-auth-page>
      <header>
        <p>Kamra Engineering Solutions</p>
        <h1>KES Electrical OS</h1>
      </header>

      <section aria-labelledby="sign-in-heading" data-auth-card>
        <h2 id="sign-in-heading">Sign in</h2>

        <form onSubmit={(event) => void submit(event)} noValidate>
          <label>
            E-mail
            <input
              type="email"
              name="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            Password
            <input
              ref={passwordInput}
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>

          {error !== null ? <p role="alert">{error}</p> : null}

          <button type="submit" disabled={pending}>
            {pending ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p data-auth-note>
          Accounts are created by the owner of your organization; there is no public sign-up. If
          you cannot sign in, ask the owner to reset your password.
        </p>
      </section>
    </main>
  );
}
