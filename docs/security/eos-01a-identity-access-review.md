# EOS-01 (a) Identity and access — security self-check

| | |
|---|---|
| Slice | EOS-01 (a) Identity and access (Master Prompt v2.1 amendment A13) |
| Reviewed state | `bee2af5` on `master`, 2026-09-20; not yet released (live is `1dda748`, which has no sign-in) |
| Kind of review | **Self-check by the implementer against the checklist below, with evidence.** It is not an independent review: the same assistant designed, wrote and checked this code together with the founder. Section 8 is the slot for an independent reviewer. |
| Evidence run | Backend gate `1063 passed` at the start of the review (100 of them in the twelve identity test files); commit `775c996` added 10 (7 cross-site, 3 for finding F16) and the F1 commit adds 6; frontend gate `365 passed` in 41 files; local browser smoke 6/6 and the Users page exercised by the founder on 2026-09-20 |

The purpose of this file is to state what was checked, what proves it, what is knowingly left
open, and what must be verified during the release. A claim without a test or a file behind it
is marked as such.

## 1. What was built

- **Sessions kept on the server.** Sign-in creates a random token; the browser holds it only in
  a cookie that is `HttpOnly`, `SameSite=Strict`, `Path=/`, host-only (no `Domain`) and `Secure`
  outside development. The database stores only the SHA-256 of the token. There is no JWT, no
  signing secret, and nothing in `localStorage` or `sessionStorage`.
- **Passwords:** argon2id (`argon2-cffi`), 12 to 128 characters, no composition rules, not blank,
  not equal to the e-mail. A hash is re-computed at sign-in when the parameters have changed.
- **Accounts:** organizations, users, memberships with the roles OWNER / ENGINEER / VIEWER. No
  public sign-up. The first owner is created by a server command that asks for the password on
  the terminal; the owner creates every other account with a first password that must be
  changed at the first sign-in. Accounts are switched off, never deleted.
- **Sign-in defence:** 5 failed attempts lock the account for 15 minutes; an unknown e-mail, a
  wrong password and a locked account get one and the same answer; an unknown e-mail costs the
  same hashing time as a known one.
- **Session life:** 12 h without activity, 7 d at most. Sign-out deletes the session on the
  server. A password change closes the user's other sessions; a reset or switching off closes
  all of them.
- **One protected router.** Public are `/health`, `/version` and `/auth/login`, `/auth/logout`
  only. Everything else needs a session (401) and a changed first password (403). Reading is
  open to every member; calculating and saving needs OWNER or ENGINEER; reference data and
  `/users` need OWNER.
- **Names on records** (`calculated_by`, submitted / approved / rejected by) come from the
  session, never from the request; a request that sends one is refused (422).
- **Audit trail:** sign-in, failure, lockout, sign-out, user created / changed, password changed
  / reset, with time, user or attempted e-mail, address and browser. Append-only.
- **Browser side:** the route guard shows no page before the server has confirmed the session;
  any API answer 401 / 403 makes the application ask the server again who is signed in.

## 2. Checklist

Result: PASS = proven by the evidence named; OPEN = see the finding; VERIFY = to be checked
during the release (section 6).

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | No route is reachable without a session unless it is on the public list | PASS | `tests/api/test_route_protection.py` walks every path of `app.openapi()`: `test_every_route_outside_the_public_list_answers_401_without_a_session`, `test_the_public_list_names_real_routes`, `test_health_and_version_stay_open_for_the_deploy_checks` |
| 2 | Roles are enforced on the server | PASS | same file: `test_a_viewer_may_read_but_not_calculate_or_save`, `test_an_engineer_may_calculate_but_not_change_reference_data`, `test_an_owner_passes_every_role_check`; `tests/api/test_users_api.py` (11) |
| 3 | A first or reset password opens nothing but the password change | PASS | `require_password_changed` on `protected_router` (`app/api/router.py`); `tests/api/test_users_api.py`; frontend `routeGuards.test.tsx` |
| 4 | Passwords are hashed with argon2id and never stored, logged or returned | PASS | `tests/core/test_security.py` (12, plus 3 added with finding F16); response schemas list their fields one by one (`app/schemas/identity.py`); no `logger.` or `print(` in the identity services and APIs (evidence run: only `create_owner.py` prints, and it prints e-mail and organization only) |
| 5 | A refused request does not echo the submitted values | PASS (code read) | `app/api/errors.py` drops `input` from every 422 and is registered in `app/main.py`; whether a test pins it was not confirmed in this review - follow-up: name the test here or add one |
| 6 | The session token never leaves the cookie | PASS | `app/api/v1/auth.py` returns no token; `tests/persistence/test_identity_models.py` (hash length 64); frontend search for `localStorage`, `sessionStorage`, `document.cookie` outside tests finds three comments and no code; `LoginPage.test.tsx` "writes nothing to browser storage" |
| 7 | Cookie name and flags | PASS locally / VERIFY live | `tests/api/test_session_cookie_name.py` (3): `__Host-` prefix, Secure, HttpOnly, SameSite=Strict, Path=/, no Domain; local browser smoke: `keos_session` HttpOnly and SameSite Strict; `Secure` is off only in development and testing and production refuses to start otherwise (`tests/core/test_identity_settings.py`, 5) |
| 8 | Lockout, single failure message, dummy verification | PASS | `tests/persistence/test_auth_service.py` (15) |
| 9 | Idle and absolute expiry, sign-out, sessions closed on password change / reset / switch-off | PASS | `tests/persistence/test_auth_service.py`, `tests/api/test_users_api.py` |
| 10 | An owner cannot demote or switch off the own account or reset the own password through user administration | PASS | `tests/api/test_users_api.py` (409); the Users page disables the own row |
| 11 | The owner bootstrap takes no password on the command line | PASS | `app/cli/create_owner.py` (getpass), `tests/persistence/test_owner_bootstrap.py` (9), `docs/operations/owner-account-runbook.md` |
| 12 | Names on records cannot be supplied by the client | PASS | `tests/api/test_run_actor.py` (3) |
| 13 | Every model table has a migration | PASS | `tests/persistence/test_migrations_cover_models.py`; migration `a7d3e9b1c5f2` proven on a local PostgreSQL (upgrade, check, downgrade, upgrade) |
| 14 | Cross-site request forgery | PASS | `SameSite=Strict`; no CORS middleware, so no preflight is answered; a simple request (form post, `text/plain`, or no `Content-Type`) is not read as JSON: `tests/api/test_cross_site_requests.py` (7), added with this review. See finding F1 for the sibling sub-domains |
| 15 | Unknown fields in requests and responses | PASS | backend requests `extra="forbid"` (`tests/schemas/test_identity_schemas.py`, 12); frontend schemas `.strict()` (`services/users.test.ts` refuses a user list that carries a `password_hash`) |
| 16 | The browser shows no page before the session is confirmed, and leaves after it has ended | PASS | `app/routeGuards.test.tsx` (17), `app/routes.test.tsx` (9), `app/AuthProvider.test.tsx` (17) |
| 17 | The return path after sign-in stays inside the application | PASS | `routeGuards.test.tsx`: absolute, protocol-relative and backslash addresses are ignored |
| 18 | Data of one organization is invisible to another | **OPEN** | finding F2 |
| 19 | Security headers, API documentation pages, host checking at the edge | VERIFY | findings F3, F4, F5 |
| 20 | Throttling of sign-in attempts per address | **OPEN** | finding F6 |
| 21 | Known vulnerabilities in dependencies | VERIFY | finding F9 |

## 3. Findings

Severity is for this product as it will run after the release: one organization, a handful of
known users, behind Cloudflare and nginx.

| ID | Severity | Finding | Decision |
|---|---|---|---|
| F1 | Medium, **fixed before the release** | **Sibling products share the registrable domain.** The other products under `kamraengineeringsolution.com` are "same-site" for a browser. `SameSite=Strict` therefore does not stop a page on a sibling sub-domain from sending requests with the session cookie. Reading answers is impossible (no CORS) and a JSON request is impossible (no preflight answer); what remains is a simple request, which the API does not read as JSON (check 14). A second effect: a sibling could set a cookie named `keos_session` for the parent domain ("cookie tossing") and so push its own session into a victim's browser. | **Decided 2026-09-20** (the founder delegated the choice to the implementer): the cookie carries the `__Host-` prefix whenever it is `Secure`. Browsers accept a `__Host-` cookie only when it is `Secure`, has `Path=/` and names no `Domain`, and only from the host itself, so a sibling can neither set nor overwrite it. The name is **derived in code** (`Settings.session_cookie_name`), not typed into the server's `.env`: every secure environment gets it, nothing is edited by hand on the server, a rollback needs no clean-up, and tests pin it (`tests/core/test_identity_settings.py` +3, `tests/api/test_session_cookie_name.py` 3, including that a planted cookie with the plain name is ignored). Plain-http development keeps `keos_session`, because the prefix needs HTTPS. Still true: keep every sibling product free of script injection; treat an XSS there as an incident for this product too. |
| F2 | High if ignored, none today | **Studies and the audit trail are not scoped to an organization.** `calculation_runs` has no organization or project link (that is EOS-01 (b)); `GET /users/events` returns the events of every organization; units and standards are shared reference data that any OWNER may change. User administration itself is scoped. With one organization nothing leaks. | **Operating rule until EOS-01 (b) is released: exactly one organization on the live system.** `create_owner` must not be used to create a second organization. EOS-01 (b) adds the organization / project link and must scope runs and events; record this in its slice plan. |
| F3 | Low | The application serves `/docs`, `/redoc` and `/openapi.json` (FastAPI defaults). They sit outside `/api/`, which is the only path nginx is known to proxy, so they should not be reachable from outside. | Checked 2026-09-20 on the live address: the three paths answer 200, and nginx proxies only `/api/` (site file, lines 20-21), so the 200 is the frontend's `index.html` from the single-page fallback, not the API documentation. The body is looked at once more in the live smoke. Follow-up all the same: switch the three pages off when `ENVIRONMENT=production`, so that a later change of the proxy cannot publish them. |
| F4 | Low | `KES_ALLOWED_HOSTS` and `KES_BACKEND_CORS_ORIGINS` exist in the settings, but `app/main.py` installs neither `TrustedHostMiddleware` nor CORS. Not installing CORS is correct and wanted (same-origin application). Host checking is left to nginx (`server_name`). | Accept. Follow-up: install `TrustedHostMiddleware` from the existing setting, or remove the unused setting, so the configuration does not promise what the code does not do. |
| F5 | Low, **confirmed** | The site file sets `X-Content-Type-Options`, `X-Frame-Options` and `Referrer-Policy` at server level, but the live answer for `/` carries none of them (checked 2026-09-20). Cause: nginx inherits `add_header` from the server level only into a location that has no `add_header` of its own; `location /` and `location /assets/` each set `Cache-Control`, so they lose the three headers. `location /api/` has none and keeps them. There is no `Strict-Transport-Security` and no `Content-Security-Policy` at all. | Fix right after the release, as its own commit and its own server step: repeat the security headers inside every location that sets a header (one included snippet), add `Strict-Transport-Security` and `Content-Security-Policy: frame-ancestors 'none'`. The file arrives through the repository and is installed with the commands in its own header; a fuller content policy follows once the font and script sources are listed. |
| F6 | Medium, accepted for now | Throttling is per account only. Anybody who knows a user's e-mail can keep that account locked (15 minutes per 5 attempts), and one address can try many e-mails. | Accept for the first release with few, known users. Follow-up before outside users are invited: a Cloudflare rate-limiting rule for `POST /api/v1/auth/login`, and a per-address counter in the application. The audit trail shows such attempts (`Sign-in failed`, `Account locked`). |
| F7 | Low | The address in the audit trail comes from `CF-Connecting-IP` / `X-Forwarded-For`. A client that reaches the origin without Cloudflare can write any value there. The address is recorded only and never used for a decision. | Accept. Follow-up: restrict ports 80 / 443 of the instance to Cloudflare's address ranges. |
| F8 | Info | No e-mail, so no self-service password reset and no notification of a reset or a lockout. The owner resets passwords and hands over first passwords personally; the owner's own recovery is the server command `create_owner --recover`. | Accept. Create a **second OWNER account** after the release so that one lost password does not need server access. |
| F9 | Info | No dependency audit was run in this slice (`pip-audit`, `npm audit`). The only new runtime dependency is `argon2-cffi`. | Run both during the release and record the result in the release row. |
| F10 | Info | No second factor. | Follow-up after EOS-01 (b); TOTP for OWNER first. |
| F11 | Info | Password rule is length only; there is no check against lists of breached passwords. | Follow-up (offline list or k-anonymity lookup). |
| F12 | Info | When a session ends while a form is half filled, the user is sent to the sign-in page and the entries are lost. | Follow-up: sign in again in place. Rare with a 12 h idle limit. |
| F13 | Info | A VIEWER sees the Calculate button; the server refuses (403) and the page shows the message. | Follow-up: hide or disable write actions for VIEWER. |
| F14 | Info | The four-eyes rule (the approver must differ from the submitter) is not enforced; decided in commit 13 to belong to the approvals slice. | Follow-up with approvals. |
| F15 | Info | A regular database backup schedule is not defined. The release takes one backup before the migration. | Follow-up in `docs/operations/deployment-runbook.md`. |
| F16 | Low, **fixed in this commit** | `verify_password` raised `AttributeError` for a missing hash (`None`) instead of answering "no match", although its own contract says a damaged hash is no match; the caller would have answered HTTP 500. Found by this review: the control case of the new cross-site tests runs a password change as the test fixture's owner, which carries no hash. Not reachable on the live system, because `users.password_hash` is `NOT NULL`. | Fixed in `app/core/security.py`: a missing or empty hash is no match and still costs one verification; `password_needs_rehash` answers True for it. Pinned by `tests/core/test_security.py` (+3) and by the control case `test_the_same_body_as_json_reaches_the_service` (HTTP 400, not 500). |

## 4. What this review did not cover

- The server: operating system, SSH access, firewall, nginx file, Cloudflare settings, database
  roles and backups. Only what `scripts/deploy.sh` and the application code show was read.
- Cryptographic review of `argon2-cffi` parameters beyond using the library defaults.
- Load, denial of service, and the behaviour under many parallel sign-ins.
- The engineering engines (unchanged by this slice).

## 5. Threats considered

Credential guessing (checks 8, F6); session theft through script (checks 6, 7); session riding
from another site (check 14, F1); privilege escalation between roles (checks 2, 3, 10);
forged authorship of records (check 12); leakage through error messages and logs (checks 4, 5, F16);
leakage between organizations (F2); open redirect after sign-in (check 17); account takeover
through recovery (F8: no remote recovery exists); a forgotten public route (check 1).

## 6. To verify during the release (commit 21)

1. Backup of the live database before `alembic upgrade head`; note the file name in the release row.
2. Production `.env`: `KES_ENVIRONMENT=production` (confirmed 2026-09-20; no session key is needed, F1 is settled in code).
3. Owner created with `create_owner` on the server; password typed there, never sent anywhere.
4. Live cookie: named `__Host-keos_session`, `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=/`, no `Domain`.
5. `curl -s -o /dev/null -w "%{http_code}"` on `/docs`, `/redoc`, `/openapi.json` of the public address: expect the frontend page or 404, not the API documentation (F3).
6. `curl -sI` on the public address: list the security headers present (F5).
7. Without a session: `GET /api/v1/auth/me` answers 401 and a study route answers 401; `/api/v1/health` answers 200.
8. `pip-audit` and `npm audit --omit=dev`; record the counts (F9).
9. Live smoke with the owner: sign-in, wrong password message, return path, change password page, sign-out, one Cable run and one Fault run carrying the owner's name in `calculated_by`.
10. Exactly one organization exists (F2).

## 7. Operating rules that follow from this review

- One organization on the live system until EOS-01 (b) is released (F2).
- First passwords are handed over personally and are changed at the first sign-in.
- A second OWNER account exists (F8).
- A script-injection defect in any sibling product is handled as an incident for this product (F1).
- Nothing is changed by hand on the server; headers and settings arrive through the repository.

## 8. Independent review

| | |
|---|---|
| Reviewer | _open_ |
| Date | _open_ |
| Scope read | _open_ |
| Result and findings | _open_ |

Until this table is filled, the status of this slice is **self-checked, not independently
reviewed**. The slice plan of 2026-09-19 asked for an independent review before the release.
No independent reviewer is available today, so the founder has to decide between waiting and
releasing on this self-check. What speaks for releasing: the live system has no sign-in at all
and every route, including the write routes of the units and standards registries, is public;
this slice closes that. What speaks against: nobody but its authors has read the code. The
decision and its date belong in `docs/project-status.md` with the release row.
