#!/usr/bin/env python3
"""Run local quality checks for scrapeer-py."""

# mypy: disallow-any-expr=False

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

_CHECK_DIRS: tuple[str, ...] = ("src/scrapeer", "tests", "scripts")
_VERIFY_SCRIPT = Path("scripts") / "verify.py"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _python_m(module: str, *module_args: str) -> list[str]:
    """Build a ``sys.executable -m module`` command (works on Windows and Unix)."""
    return [sys.executable, "-m", module, *module_args]


def _run_step(name: str, args: Sequence[str], *, cwd: Path | None = None) -> None:
    """Run a subprocess step; raise SystemExit on non-zero exit code."""
    print(f"==> {name}")
    result = subprocess.run(
        list(args),
        cwd=cwd if cwd is not None else _repo_root(),
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"Step failed: {name} (exit code {result.returncode})")


def _format_paths() -> list[str]:
    return list(_CHECK_DIRS)


def _autopep8_args(*, fix: bool) -> list[str]:
    args = _python_m("autopep8", "--select=W291,W293", "-r", *_format_paths())
    mode_flag = "--in-place" if fix else "--diff"
    args.insert(3, mode_flag)
    return args


def _isort_args(*, fix: bool) -> list[str]:
    args = _python_m("isort", *_format_paths())
    if not fix:
        args.insert(3, "--check-only")
    return args


def main() -> None:
    """Execute formatting, linting, security, and test checks."""
    parser = argparse.ArgumentParser(description="Run scrapeer-py quality checks.")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply autopep8 and isort fixes before running checks",
    )
    namespace = parser.parse_args()
    fix_enabled: bool = bool(namespace.fix)

    root = _repo_root()
    pylint_report = root / "pylint-report.txt"
    verify_script = str(_VERIFY_SCRIPT)
    format_paths = _format_paths()

    steps: list[tuple[str, list[str]]] = [
        ("autopep8 (trailing whitespace)", _autopep8_args(fix=fix_enabled)),
        ("isort", _isort_args(fix=fix_enabled)),
        ("black", _python_m("black", "--check", *format_paths)),
        (
            "mypy",
            _python_m(
                "mypy",
                "src/scrapeer",
                "tests",
                verify_script,
                str(root / "scripts" / "generate_file_version_info.py"),
            ),
        ),
        (
            "pylint (package)",
            _python_m(
                "pylint",
                "src/scrapeer",
                f"--output={pylint_report}",
            ),
        ),
        ("pylint (verify)", _python_m("pylint", verify_script)),
        (
            "pylint (version info)",
            _python_m(
                "pylint",
                str(root / "scripts" / "generate_file_version_info.py"),
            ),
        ),
        (
            "bandit",
            _python_m(
                "bandit",
                "-r",
                "src/scrapeer",
                "-q",
                "-c",
                "pyproject.toml",
            ),
        ),
        (
            "pip-audit",
            _python_m("pip_audit", "-r", "requirements-dev.txt"),
        ),
        ("pytest", _python_m("pytest")),
    ]

    for name, step_args in steps:
        _run_step(name, step_args, cwd=root)

    print("All verification steps passed.")


if __name__ == "__main__":
    main()
