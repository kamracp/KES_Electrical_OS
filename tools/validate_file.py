#!/usr/bin/env python3
"""Validate one KES Electrical OS file and report all applicable failures."""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def find_tool(*candidates: Path | str) -> str:
    for candidate in candidates:
        if isinstance(candidate, Path) and candidate.is_file():
            return str(candidate)
        if isinstance(candidate, str) and (resolved := shutil.which(candidate)):
            return resolved
    return str(candidates[0])


def resolve_target(value: str) -> Path:
    supplied = Path(value).expanduser()
    target = supplied.resolve() if supplied.is_absolute() else (ROOT / supplied).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError("target must remain inside the repository")
    if not target.is_file():
        raise ValueError(f"target file does not exist: {target.relative_to(ROOT)}")
    return target


def backend_test_targets(target: Path, extra: list[str]) -> list[str]:
    relative = target.relative_to(BACKEND)
    selected: set[Path] = {target} if relative.parts[0] == "tests" else set()
    if relative.parts[:2] in {("app", "domain"), ("tests", "domain")}:
        topic = target.parent.name
    else:
        topic = target.stem.removeprefix("test_")
        for suffix in ("_engine", "_models", "_results"):
            topic = topic.removesuffix(suffix)

    if relative.parts[0] != "tests":
        selected.update((BACKEND / "tests").rglob(f"test_{target.stem}.py"))
    api_test = BACKEND / "tests/api" / f"test_{topic}.py"
    if api_test.is_file():
        selected.add(api_test)
    domain_root = BACKEND / "tests/domain"
    if domain_root.is_dir():
        selected.update(path for path in domain_root.rglob(topic) if path.is_dir())

    directories = {path for path in selected if path.is_dir()}
    selected = {
        path
        for path in selected
        if path.is_dir() or not any(path.is_relative_to(directory) for directory in directories)
    }
    return [
        *(str(path.relative_to(BACKEND)) for path in sorted(selected)),
        *extra,
    ]


def frontend_test_targets(target: Path, extra: list[str]) -> list[str]:
    selected: set[Path] = set()
    if ".test." in target.name or ".spec." in target.name:
        selected.add(target)
    else:
        for pattern in (f"{target.stem}.test.*", f"{target.stem}.spec.*"):
            selected.update(path for path in (FRONTEND / "src").rglob(pattern) if path.is_file())
    return [
        *(str(path.relative_to(FRONTEND)) for path in sorted(selected)),
        *extra,
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate one file without formatting, staging, committing, or pushing."
    )
    parser.add_argument("file", help="Repository-relative or absolute target file.")
    parser.add_argument(
        "--test",
        action="append",
        default=[],
        help="Additional focused test path or node; repeat when needed.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip full regression after focused checks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        target = resolve_target(args.file)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    relative = target.relative_to(ROOT)
    checks: list[tuple[str, Path, list[str], str]] = []
    notices: list[tuple[str, str]] = []
    python = find_tool(ROOT / ".venv/bin/python", ROOT / "venv/bin/python", sys.executable)
    ruff = find_tool(ROOT / ".venv/bin/ruff", ROOT / "venv/bin/ruff", "ruff")

    try:
        content = target.read_text(encoding="utf-8")
        trailing = [
            number
            for number, line in enumerate(content.splitlines(), start=1)
            if line.rstrip(" \t") != line
        ]
        hygiene_issues = []
        if trailing:
            hygiene_issues.append("trailing whitespace: " + ", ".join(map(str, trailing[:8])))
        if content and not content.endswith("\n"):
            hygiene_issues.append("missing final newline")
    except UnicodeDecodeError:
        hygiene_issues = []
        notices.append(("SKIP", "Text hygiene: non-UTF-8 target"))

    if target.suffix == ".py":
        if target.is_relative_to(BACKEND):
            cwd = BACKEND
            file_arg = str(target.relative_to(BACKEND))
            ruff_base = [ruff]
        else:
            cwd = ROOT
            file_arg = str(relative)
            ruff_base = [ruff, "--config", str(BACKEND / "pyproject.toml")]
        checks.extend(
            [
                (
                    "Ruff format check",
                    cwd,
                    [*ruff_base, "format", "--check", file_arg],
                    f"Run Ruff format on {file_arg} and review the diff.",
                ),
                (
                    "Ruff lint",
                    cwd,
                    [*ruff_base, "check", file_arg],
                    "Resolve each Ruff diagnostic in the target file.",
                ),
                (
                    "Python compile",
                    ROOT,
                    [python, "-m", "py_compile", str(target)],
                    "Correct the reported Python syntax error.",
                ),
            ]
        )
        if target.is_relative_to(BACKEND):
            tests = backend_test_targets(target, args.test)
            if tests:
                checks.append(
                    (
                        "Focused/module backend tests",
                        BACKEND,
                        [python, "-m", "pytest", *tests, "-q"],
                        "Inspect the first failure and preserve Decimal determinism.",
                    )
                )
            else:
                notices.append(("WARN", "No backend test inferred; use --test."))
            if not args.quick:
                checks.append(
                    (
                        "Full backend regression",
                        BACKEND,
                        [python, "-m", "pytest", "tests", "-q"],
                        "Inspect the first regression failure.",
                    )
                )
        else:
            notices.append(("SKIP", "Backend tests: target is outside backend."))
    elif target.is_relative_to(FRONTEND):
        binaries = FRONTEND / "node_modules/.bin"
        frontend_file = str(target.relative_to(FRONTEND))
        if target.suffix in {".js", ".jsx", ".ts", ".tsx"}:
            checks.append(
                (
                    "Oxlint",
                    FRONTEND,
                    [str(binaries / "oxlint"), frontend_file],
                    "Resolve lint diagnostics in the target file.",
                )
            )
        else:
            notices.append(("SKIP", "Oxlint: target is not JavaScript or TypeScript."))
        checks.append(
            (
                "TypeScript project check",
                FRONTEND,
                [str(binaries / "tsc"), "-b", "--pretty", "false"],
                "Resolve the TypeScript error without weakening types.",
            )
        )
        tests = frontend_test_targets(target, args.test)
        if tests:
            checks.append(
                (
                    "Focused frontend tests",
                    FRONTEND,
                    [str(binaries / "vitest"), "run", *tests],
                    "Inspect the failing Vitest assertion or environment.",
                )
            )
        else:
            notices.append(("WARN", "No frontend test inferred; use --test."))
        if not args.quick:
            checks.append(
                (
                    "Full frontend tests",
                    FRONTEND,
                    [str(binaries / "vitest"), "run"],
                    "Inspect the first frontend regression failure.",
                )
            )
        checks.append(
            (
                "Vite production build",
                FRONTEND,
                [str(binaries / "vite"), "build"],
                "Resolve bundling or production-build errors.",
            )
        )
    else:
        notices.append(("SKIP", "No language-specific validation profile."))

    checks.extend(
        [
            (
                "Git working-tree diff check",
                ROOT,
                ["git", "diff", "--check", "--", str(relative)],
                "Remove whitespace errors from the target file.",
            ),
            (
                "Git cached diff check",
                ROOT,
                ["git", "diff", "--cached", "--check", "--", str(relative)],
                "Correct staged whitespace errors before committing.",
            ),
        ]
    )

    print(f"KES Electrical OS validator: {relative}")
    print("Mode: quick" if args.quick else "Mode: exhaustive")
    results: list[tuple[str, str, float]] = []
    if hygiene_issues:
        print(f"[FAIL] Text hygiene — {'; '.join(hygiene_issues)}")
        results.append(("Text hygiene", "FAIL", 0))
    elif not any("Text hygiene" in notice for _, notice in notices):
        print("[PASS] Text hygiene")
        results.append(("Text hygiene", "PASS", 0))

    for name, cwd, command, hint in checks:
        print(f"\n== {name} ==\n$ {shlex.join(command)}")
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            elapsed = time.perf_counter() - started
            print(f"[FAIL] Executable not found. {hint}")
            results.append((name, "FAIL", elapsed))
            continue
        elapsed = time.perf_counter() - started
        if completed.stdout:
            print(completed.stdout.rstrip())
        if completed.stderr:
            print(completed.stderr.rstrip(), file=sys.stderr)
        status = "PASS" if completed.returncode == 0 else "FAIL"
        detail = "" if status == "PASS" else f" Exit {completed.returncode}. {hint}"
        print(f"[{status}] {name}{detail}")
        results.append((name, status, elapsed))

    status_output = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    changed = [line[3:].strip().split(" -> ")[-1] for line in status_output.stdout.splitlines()]
    unrelated = [path for path in changed if path != str(relative)]
    if status_output.returncode:
        scope_status = "FAIL"
        scope_detail = "unable to read Git status"
    elif unrelated:
        scope_status = "WARN"
        scope_detail = "unrelated changes preserved: " + ", ".join(unrelated)
    else:
        scope_status = "PASS"
        scope_detail = status_output.stdout.strip() or "clean"
    notices.append((scope_status, f"Git one-file scope: {scope_detail}"))

    for status, notice in notices:
        print(f"[{status}] {notice}")
        results.append((notice.split(":", 1)[0], status, 0))

    print(f"\n== Summary: {relative} ==")
    for name, status, elapsed in results:
        print(f"{status:4}  {name:<32} {elapsed:>7.2f}s")
    states = ("PASS", "WARN", "FAIL", "SKIP")
    counts = {state: sum(result[1] == state for result in results) for state in states}
    print("  ".join(f"{state}={counts[state]}" for state in states))
    if counts["FAIL"]:
        print("Validation failed; review every failure above.")
        return 1
    print("Validation passed; nothing was formatted, staged, committed, or pushed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
