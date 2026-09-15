# AGENTS.md — KES Electrical OS development preflight

This file binds every development session (human or AI assistant). It condenses the Enterprise Master Prompt v2.0 into a checklist; the prompt, ADRs and `docs/references/` remain the controlled sources.

## 1. Session start (always, read-only first)

1. `git status --short` — inspect the live tree. A clean remote never implies a clean local tree.
2. `git log --oneline -3` and confirm `master` == `origin/master`.
3. Re-read: `docs/adr/0001-system-architecture.md`, `docs/adr/0002-engineering-units-and-rounding.md`, `docs/references/electrical-master-reference-register.md`, and the focused tests of any module you will touch.
4. Never overwrite, delete, reset, clean, stash-drop or discard existing local work or untracked files.

## 2. One-file workflow (every change)

Inspect → Design → Code (exactly one file) → Validate → Test (focused first) → Git review → `git add <exact-file>` → `git diff --cached --check` → Commit (one milestone message) → Push `master` → Verify.

- Never `git add .`, `git add -A`, `git commit -a`, `git reset --hard`, `git clean`, or force-push.
- One short single-line terminal command at a time; the user pastes only what is inside code boxes.
- Explanations in Hindi; code, identifiers, filenames, file contents, commit messages and commands in English.
- After each completed file report the completion countdown (file N/T, function, validation evidence, commit, next).

## 3. Validation gates

| Scope | Command | Gate |
|---|---|---|
| Any single file | `python tools/validate_file.py <path>` | all applicable checks pass |
| Backend file | `ruff format <file> && ruff check <file>`; `python -m py_compile <file>` | clean |
| Backend focused | `pytest <focused tests> -q` | pass |
| Backend regression | `pytest backend/tests -q` (coverage gate per `pyproject`) | pass before push of engine changes |
| Frontend file | `npx oxlint <file>`; `npx tsc -b --noEmit` | clean |
| Frontend | `npx vitest run <adjacent test>`; `npm run build` | pass |
| Migrations | `alembic heads` shows exactly one head; `alembic upgrade head` on a scratch DB | pass before commit |

Claims of "passed", "committed", "pushed" or "deployed" require the command output as evidence.

## 4. Engineering invariants (never relax)

- Deterministic `Decimal` arithmetic with explicit units and controlled rounding (ADR-0002); no float in engines or persisted engineering values.
- Engines depend on nothing outside `backend/app/domain/`; no DB, HTTP, UI or manufacturer catalog imports.
- Every result carries inputs, assumptions, method/formula id, reference ids, engine version, warnings and notes; notes propagate unchanged through API and UI.
- Canonical design-check statuses only (see prompt §5.1): a successful calculation is never a compliance conclusion.
- Approved calculation runs are immutable and reproducible; corrections create a new revision.
- Safety-critical engines (fault, protection, earthing, lightning) require independent engineering review recorded in `docs/references/independent-review-register.md` before any release claim.
- Tenant isolation: every persisted enterprise record is scoped by organization/project; no cross-tenant reads.

## 5. Reference preflight (before citing any standard)

1. The reference must exist in `docs/references/electrical-master-reference-register.md` with a `reference_id`.
2. Cite by `reference_id` + clause/table locator; never free-text standard names in engines.
3. Only `VERIFIED` records may support `COMPLIANCE_READY`. `UNVERIFIED`, `UNRESOLVED`, `LEGACY`, `REFERENCE_ONLY` inform design checks only.
4. Editions and amendments are never inferred; a missing edition is logged in `docs/references/reference-gap-register.md`.
5. No clause text or copyrighted content is committed; bibliographic metadata and non-copyrighted rule summaries only.
6. Known open item: the string `IEC 60909-0:2026` in the fault engine is unverified (`REF-IEC-60909-0`, status UNRESOLVED).

## 6. Scope discipline

- Work the active release slice only; do not start new modules, refactors or renames mid-slice.
- Report blockers (permission, destructive action, standards gap, migration conflict, scope creep) and stop.
- Deployment readiness (prompt §22) is reported separately from EOS-01..EOS-15 roadmap completeness.

## 7. Current pointer

Active sequence: Enterprise Master Prompt v2.0 §15. Governance files done: reference register (`6100ce5`), this file. Next: Cable frontend vertical slice (`frontend/src/services/cable.ts` onward).
