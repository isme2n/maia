"""Executable entrypoints for Maia."""

from __future__ import annotations

from collections.abc import Sequence

from .cli import main as cli_main


def main(argv: Sequence[str] | None = None) -> int:
    return cli_main(argv)
