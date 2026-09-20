import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import "../styles/users.css";
import { useAuth } from "../app/authContext";
import { ROLE_LABELS } from "../app/roles";
import { organizationRoleSchema, type OrganizationRole } from "../services/auth";
import {
  createUser,
  listAuthEvents,
  listUsers,
  resetUserPassword,
  updateUser,
  type AuthEventType,
  type NewUser,
  type User,
  type UserChange,
} from "../services/users";
import { PASSWORD_MIN_LENGTH, describePasswordProblem } from "../utils/passwordPolicy";

// User administration for the owner of the organization (EOS-01 a).
//
// There is no public sign-up and no deletion: the owner creates an account with a first
// password (which the user must change at the first sign-in), changes a role, switches an
// account off or on, and resets a password. The server enforces all of it again; this page
// only refuses what it can already see is wrong. A refusal for access reasons (HTTP 401 /
// 403) is picked up by the AuthProvider, which asks the server again who is signed in.

const USERS_KEY = ["users", "list"] as const;
const EVENTS_KEY = ["users", "events"] as const;

const EVENT_LABELS: Record<AuthEventType, string> = {
  LOGIN_SUCCEEDED: "Signed in",
  LOGIN_FAILED: "Sign-in failed",
  LOGIN_LOCKED: "Account locked",
  LOGOUT: "Signed out",
  USER_CREATED: "User created",
  USER_UPDATED: "User changed",
  PASSWORD_CHANGED: "Password changed",
  PASSWORD_RESET: "Password reset",
};

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

type NewUserDraft = { fullName: string; email: string; role: OrganizationRole; password: string };

const EMPTY_DRAFT: NewUserDraft = { fullName: "", email: "", role: "ENGINEER", password: "" };

function describeFailure(caught: unknown, fallback: string): string {
  return caught instanceof Error && caught.message.trim() !== "" ? caught.message : fallback;
}

function formatDateTime(value: string | null): string {
  if (value === null) {
    return "Never";
  }

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function describeStatus(user: User): string {
  if (!user.is_active) {
    return "Switched off";
  }
  if (user.locked_until !== null && new Date(user.locked_until).getTime() > Date.now()) {
    return `Locked until ${formatDateTime(user.locked_until)}`;
  }
  if (user.must_change_password) {
    return "Password change due";
  }
  return "Active";
}

function checkNewUser(draft: NewUserDraft): string | null {
  if (draft.fullName.trim() === "") {
    return "Full name is required.";
  }
  if (draft.email.trim() === "") {
    return "E-mail is required.";
  }
  if (!EMAIL_PATTERN.test(draft.email.trim())) {
    return "Enter a valid e-mail address, for example name@company.com.";
  }
  return describePasswordProblem(draft.password, draft.email, "First password");
}

export function UsersPage() {
  const { state } = useAuth();
  const queryClient = useQueryClient();
  const session = state.status === "signed-in" ? state.session : null;
  const isOwner = session?.role === "OWNER";

  const [draft, setDraft] = useState<NewUserDraft>(EMPTY_DRAFT);
  const [showPasswords, setShowPasswords] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);
  const [resetTarget, setResetTarget] = useState<User | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resetError, setResetError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const usersQuery = useQuery({
    queryKey: USERS_KEY,
    queryFn: ({ signal }) => listUsers(signal),
    enabled: isOwner,
  });
  const eventsQuery = useQuery({
    queryKey: EVENTS_KEY,
    queryFn: ({ signal }) => listAuthEvents(50, signal),
    enabled: isOwner,
  });

  function reload(): Promise<void> {
    return queryClient.invalidateQueries({ queryKey: ["users"] });
  }

  const createMutation = useMutation({
    mutationFn: (user: NewUser) => createUser(user),
    onSuccess: reload,
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, change }: { id: string; change: UserChange }) => updateUser(id, change),
    onSuccess: reload,
  });
  const resetMutation = useMutation({
    mutationFn: ({ id, password }: { id: string; password: string }) =>
      resetUserPassword(id, password),
    onSuccess: reload,
  });

  if (session === null) {
    return null;
  }

  if (!isOwner) {
    return (
      <main data-users-page>
        <header>
          <p>EOS-01 · Identity and access</p>
          <h1>Users</h1>
        </header>
        <p role="alert">Only the owner of the organization can manage users.</p>
      </main>
    );
  }

  const busy = createMutation.isPending || updateMutation.isPending || resetMutation.isPending;
  const nameOf = new Map((usersQuery.data ?? []).map((user) => [user.id, user.full_name]));

  async function submitNewUser(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setNotice(null);

    const problem = checkNewUser(draft);

    if (problem !== null) {
      setCreateError(problem);
      return;
    }

    setCreateError(null);

    try {
      const created = await createMutation.mutateAsync({
        full_name: draft.fullName.trim(),
        email: draft.email.trim(),
        role: draft.role,
        password: draft.password,
      });
      setDraft(EMPTY_DRAFT);
      setNotice(
        `${created.full_name} was created. Give them the first password yourself; they must change it at the first sign-in.`,
      );
    } catch (caught) {
      setCreateError(describeFailure(caught, "The user was not created."));
    }
  }

  async function change(user: User, update: UserChange, done: string): Promise<void> {
    setRowError(null);
    setNotice(null);

    try {
      await updateMutation.mutateAsync({ id: user.id, change: update });
      setNotice(done);
    } catch (caught) {
      setRowError(describeFailure(caught, "The user was not changed."));
    }
  }

  function openReset(user: User): void {
    setResetTarget(user);
    setResetPassword("");
    setResetError(null);
    setNotice(null);
  }

  async function submitReset(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    if (resetTarget === null) {
      return;
    }

    const problem = describePasswordProblem(resetPassword, resetTarget.email, "New password");

    if (problem !== null) {
      setResetError(problem);
      return;
    }

    setResetError(null);

    try {
      await resetMutation.mutateAsync({ id: resetTarget.id, password: resetPassword });
      setNotice(
        `The password of ${resetTarget.full_name} was reset and their sessions were closed. They must change it at the next sign-in.`,
      );
      setResetTarget(null);
      setResetPassword("");
    } catch (caught) {
      setResetError(describeFailure(caught, "The password was not reset."));
    }
  }

  return (
    <main data-users-page>
      <header>
        <p>EOS-01 · Identity and access</p>
        <h1>Users</h1>
        <p>
          Accounts of {session.organization.name}. There is no public sign-up: the owner creates
          every account. Accounts are switched off, never deleted, so the names on calculation
          runs and in the audit trail keep their meaning.
        </p>
      </header>

      {notice !== null ? <p role="status">{notice}</p> : null}

      <section aria-label="User list">
        <h2>User list</h2>

        {usersQuery.isPending ? <p data-users-note>Loading the users…</p> : null}
        {usersQuery.isError ? (
          <p role="alert">
            {describeFailure(usersQuery.error, "The user list could not be loaded.")}
          </p>
        ) : null}
        {rowError !== null ? <p role="alert">{rowError}</p> : null}

        {usersQuery.data !== undefined ? (
          <div data-table-scroll>
            <table>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">E-mail</th>
                  <th scope="col">Role</th>
                  <th scope="col">Status</th>
                  <th scope="col">Last sign-in</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {usersQuery.data.map((user) => {
                  const own = user.id === session.user.id;
                  return (
                    <tr key={user.id} data-user-id={user.id} data-user-active={user.is_active}>
                      <th scope="row">
                        {user.full_name}
                        {own ? " (you)" : ""}
                      </th>
                      <td>{user.email}</td>
                      <td>
                        <select
                          aria-label={`Role of ${user.full_name}`}
                          value={user.role}
                          disabled={own || busy}
                          onChange={(event) => {
                            const role = organizationRoleSchema.parse(event.target.value);
                            void change(
                              user,
                              { role },
                              `${user.full_name} is now ${ROLE_LABELS[role]}.`,
                            );
                          }}
                        >
                          {organizationRoleSchema.options.map((role) => (
                            <option key={role} value={role}>
                              {ROLE_LABELS[role]}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>{describeStatus(user)}</td>
                      <td>{formatDateTime(user.last_login_at)}</td>
                      <td>
                        {own ? (
                          <span data-users-note>Use Change password in the top bar.</span>
                        ) : (
                          <span data-row-actions>
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                void change(
                                  user,
                                  { is_active: !user.is_active },
                                  user.is_active
                                    ? `${user.full_name} was switched off and their sessions were closed.`
                                    : `${user.full_name} was switched on.`,
                                )
                              }
                            >
                              {user.is_active ? "Switch off" : "Switch on"}
                            </button>
                            <button type="button" disabled={busy} onClick={() => openReset(user)}>
                              Reset password
                            </button>
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {resetTarget !== null ? (
        <section aria-label="Reset password">
          <h2>Reset the password of {resetTarget.full_name}</h2>
          <form onSubmit={(event) => void submitReset(event)} noValidate>
            <label>
              New password
              <input
                type={showPasswords ? "text" : "password"}
                name="reset-password"
                autoComplete="new-password"
                value={resetPassword}
                onChange={(event) => setResetPassword(event.target.value)}
              />
            </label>
            {resetError !== null ? <p role="alert">{resetError}</p> : null}
            <p data-form-actions>
              <button type="submit" disabled={busy}>
                {resetMutation.isPending ? "Resetting…" : "Reset password"}
              </button>
              <button type="button" onClick={() => setResetTarget(null)}>
                Cancel
              </button>
            </p>
          </form>
        </section>
      ) : null}

      <section aria-label="Add a user">
        <h2>Add a user</h2>
        <form onSubmit={(event) => void submitNewUser(event)} noValidate>
          <fieldset disabled={busy}>
            <legend>New account</legend>
            <label>
              Full name
              <input
                type="text"
                name="full-name"
                autoComplete="off"
                value={draft.fullName}
                onChange={(event) => setDraft({ ...draft, fullName: event.target.value })}
              />
            </label>
            <label>
              E-mail
              <input
                type="email"
                name="new-user-email"
                autoComplete="off"
                value={draft.email}
                onChange={(event) => setDraft({ ...draft, email: event.target.value })}
              />
            </label>
            <label>
              Role
              <select
                name="role"
                value={draft.role}
                onChange={(event) =>
                  setDraft({ ...draft, role: organizationRoleSchema.parse(event.target.value) })
                }
              >
                {organizationRoleSchema.options.map((role) => (
                  <option key={role} value={role}>
                    {ROLE_LABELS[role]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              First password
              <input
                type={showPasswords ? "text" : "password"}
                name="first-password"
                autoComplete="new-password"
                value={draft.password}
                onChange={(event) => setDraft({ ...draft, password: event.target.value })}
              />
            </label>
            <label>
              <input
                type="checkbox"
                checked={showPasswords}
                onChange={(event) => setShowPasswords(event.target.checked)}
              />
              Show passwords while typing
            </label>
            <p>
              Owner: everything, including users. Engineer: runs and saves studies. Viewer: reads
              only. The first password needs at least {PASSWORD_MIN_LENGTH} characters and must
              be changed by the user at the first sign-in.
            </p>
          </fieldset>
          {createError !== null ? <p role="alert">{createError}</p> : null}
          <button type="submit" disabled={busy}>
            {createMutation.isPending ? "Creating…" : "Create user"}
          </button>
        </form>
      </section>

      <section aria-label="Audit trail">
        <h2>Audit trail</h2>
        <p data-users-note>The last 50 sign-in and user-administration events, newest first.</p>

        {eventsQuery.isPending ? <p data-users-note>Loading the audit trail…</p> : null}
        {eventsQuery.isError ? (
          <p role="alert">
            {describeFailure(eventsQuery.error, "The audit trail could not be loaded.")}
          </p>
        ) : null}

        {eventsQuery.data !== undefined ? (
          <div data-table-scroll>
            <table>
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">Event</th>
                  <th scope="col">User</th>
                  <th scope="col">From</th>
                  <th scope="col">Detail</th>
                </tr>
              </thead>
              <tbody>
                {eventsQuery.data.map((event) => (
                  <tr key={event.id} data-event-type={event.event_type}>
                    <td>{formatDateTime(event.occurred_at)}</td>
                    <td>{EVENT_LABELS[event.event_type]}</td>
                    <td>
                      {(event.user_id !== null ? nameOf.get(event.user_id) : undefined) ??
                        event.email_attempted ??
                        "—"}
                    </td>
                    <td>{event.ip_address ?? "—"}</td>
                    <td>{event.detail ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  );
}
