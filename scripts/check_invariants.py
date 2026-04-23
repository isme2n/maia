#!/usr/bin/env python3
"""Lightweight Maia contract and policy checks."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from maia import __version__
from maia.cli_parser import INSTALL_EXAMPLES, PUBLIC_ONBOARDING_CONTRACT
from maia.public_contract import (
    HERMES_INSTALL_SCRIPT_URL,
    MAIA_GIT_INSTALL_SPEC,
    MAIA_INSTALL_CURL_COMMAND,
    MAIA_INSTALL_REF,
    MAIA_INSTALL_SCRIPT_URL,
)

README_PATH = REPO_ROOT / "README.md"
INSTALL_SCRIPT_PATH = REPO_ROOT / "scripts" / "install.sh"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

_POLICY_RULES = (
    (
        "silent-fallback",
        "Possible silent fallback or quiet failure masking",
        re.compile(r"\b(fallback|fallbackTo|default on error|silent fallback)\b", re.IGNORECASE),
        re.compile(r"maia-allow-failover", re.IGNORECASE),
    ),
    (
        "legacy-shadow-path",
        "Possible legacy or shadow path",
        re.compile(r"\b(legacy|shadow path|compat(?:ibility)? path|deprecated write path)\b", re.IGNORECASE),
        re.compile(r"maia-allow-legacy", re.IGNORECASE),
    ),
    (
        "dual-write",
        "Possible dual-write or mirror-write pattern",
        re.compile(r"\b(dual[- ]write|mirror[- ]write|write both|fan[- ]out write|transitional-json-cache)\b", re.IGNORECASE),
        re.compile(r"maia-allow-dual-write", re.IGNORECASE),
    ),
)

_IGNORE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
    "node_modules",
}
_TEXT_SUFFIXES = {".py", ".md", ".sh", ".toml", ".yml", ".yaml", ".json"}


def _canonical_contract_errors() -> list[str]:
    errors: list[str] = []
    readme = README_PATH.read_text(encoding="utf-8")
    install_script = INSTALL_SCRIPT_PATH.read_text(encoding="utf-8")
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    expected_pyproject_version = f'version = "{__version__}"'
    if expected_pyproject_version not in pyproject:
        errors.append(f"pyproject.toml must expose package version {__version__}.")

    expected_ref_line = f'MAIA_INSTALL_REF="${{MAIA_INSTALL_REF:-{MAIA_INSTALL_REF}}}"'
    if expected_ref_line not in install_script:
        errors.append(
            f"scripts/install.sh must default MAIA_INSTALL_REF to {MAIA_INSTALL_REF}."
        )

    help_default_line = f"MAIA_INSTALL_REF       Git ref to install (default: {MAIA_INSTALL_REF})"
    if help_default_line not in install_script:
        errors.append("scripts/install.sh help text must expose the canonical tagged install ref.")

    if HERMES_INSTALL_SCRIPT_URL not in install_script:
        errors.append("scripts/install.sh lost the canonical Hermes installer URL.")

    if MAIA_INSTALL_CURL_COMMAND not in readme:
        errors.append("README.md must expose the canonical curl install command.")

    fallback_line = f"Install directly from GitHub with uv: `uv tool install '{MAIA_GIT_INSTALL_SPEC}'`"
    if fallback_line not in readme:
        errors.append("README.md must expose the canonical tagged uv install fallback.")

    if MAIA_INSTALL_CURL_COMMAND not in INSTALL_EXAMPLES:
        errors.append("cli_parser.INSTALL_EXAMPLES must use the canonical install command.")

    onboarding_line = f"Primary OSS install path: `{MAIA_INSTALL_CURL_COMMAND}`."
    if onboarding_line not in PUBLIC_ONBOARDING_CONTRACT:
        errors.append("cli_parser.PUBLIC_ONBOARDING_CONTRACT must use the canonical install command.")

    forbidden_refs = ("git+https://github.com/isme2n/maia.git@main", "raw.githubusercontent.com/isme2n/maia/main")
    for path in (README_PATH, INSTALL_SCRIPT_PATH, REPO_ROOT / "src" / "maia" / "cli_parser.py"):
        text = path.read_text(encoding="utf-8")
        for forbidden in forbidden_refs:
            if forbidden in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} still contains main-tracking install ref: {forbidden}")

    return errors


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in _IGNORE_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix not in _TEXT_SUFFIXES:
            continue
        yield path


def _policy_scan(root: Path) -> list[tuple[str, Path, int, str, str]]:
    findings: list[tuple[str, Path, int, str, str]] = []
    for path in _iter_text_files(root):
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule_id, description, pattern, allow_pattern in _POLICY_RULES:
                if not pattern.search(line):
                    continue
                if allow_pattern.search(line):
                    continue
                findings.append((rule_id, path, line_number, description, line.strip()))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Maia contract invariants and policy smells.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("contracts", help="Fail if the canonical release/install contract drifted")

    scan_parser = subparsers.add_parser(
        "scan",
        help="Heuristic scan for legacy/fallback/dual-write/shadow-path smells",
    )
    scan_parser.add_argument("path", nargs="?", default=".", help="Path to scan")
    scan_parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit non-zero when heuristic findings are present",
    )

    args = parser.parse_args(argv)

    if args.command == "contracts":
        errors = _canonical_contract_errors()
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("Maia contract check passed.")
        return 0

    findings = _policy_scan((REPO_ROOT / args.path).resolve() if not Path(args.path).is_absolute() else Path(args.path))
    if not findings:
        print(f"No heuristic policy-scan findings in {args.path}")
        return 0

    for rule_id, path, line_number, description, line in findings:
        try:
            relative = path.relative_to(REPO_ROOT)
        except ValueError:
            relative = path
        print(f"[{rule_id}] {relative}:{line_number}")
        print(f"  {description}")
        print(f"  {line}")

    return 1 if args.fail_on_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
