# Owner account runbook (EOS-01 a)

KES Electrical OS has no public sign-up. Owners create all other users in the application
(Users page). Two situations cannot be settled inside the application and are handled by a
command on the server: creating the first owner, and recovering an owner who is locked out.

Who may do this: only a person with shell access to the server. The command is not reachable
over HTTP.

## Rules

- The password is typed at the prompt; it is not shown. Never put a password on a command
  line, in a script, in a chat or in a file: command lines are kept in the shell history.
- Use a passphrase of 12 characters or more that is used nowhere else.
- The command changes data only. It does not edit code or configuration on the server.

## 1. Create the first owner (once, at the first release with sign-in)

Run after the release, when `alembic upgrade head` has created the identity tables.

    ssh <server>
    cd /opt/kes-electrical-os/backend
    ../.venv/bin/python -m app.cli.create_owner

Answer the prompts: organization code (for example `KES`), organization name, owner e-mail,
owner full name, password (twice). Expected last line:

    Owner created: <e-mail> in new organization KES.

Then open the site, sign in, and create the other users on the Users page.

A second owner for the same organization can be created the same way (the organization name
is ignored when the code already exists), or by an owner on the Users page.

## 2. Recover owner access (emergency)

Use when the only owner forgot the password, was deactivated, or lost the owner role.

    cd /opt/kes-electrical-os/backend
    ../.venv/bin/python -m app.cli.create_owner --recover

Answer: organization code, the existing user's e-mail, a new password (twice). The command
reactivates the user, makes the user an owner again, removes a lock, sets the password and
closes all open sessions of that user. Expected last line:

    Owner recovered: <e-mail> in organization KES.

The recovery is written to the audit trail ("owner access recovered by the server command")
and is visible to every owner under Users, Audit trail.

## 3. When the command refuses

| Message | Meaning |
|---|---|
| `The two passwords differ; nothing was changed.` | Type the same password twice. |
| `Refused: Password must have at least 12 characters.` | Choose a longer passphrase. |
| `Refused: A user with this e-mail already exists...` | Use `--recover`, or another e-mail. |
| `Refused: Recovery needs an existing organization code...` | Check the code and the e-mail. |
| A database connection error | Run from `backend/` so that `.env` is found; check the service. |
