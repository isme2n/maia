#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

START_MARKER = "REVIEW_RESULT_START"
END_MARKER = "REVIEW_RESULT_END"
BLOCK_PATTERN = re.compile(
    rf"{START_MARKER}(.*?){END_MARKER}",
    re.DOTALL,
)
VERDICT_PATTERN = re.compile(r"^verdict:\s*(approve|request_changes)\s*$", re.MULTILINE)


def _read_input(argv: list[str]) -> str:
    if len(argv) > 2:
        raise SystemExit("usage: python3 scripts/codex-parse-review.py [review-output-file]")
    if len(argv) == 2:
        return Path(argv[1]).read_text(encoding="utf-8")
    return sys.stdin.read()


def parse_review(text: str) -> dict[str, str]:
    blocks = [match.group(1).strip() for match in BLOCK_PATTERN.finditer(text)]

    if not blocks:
        raise ValueError("missing review result markers")

    for block in reversed(blocks):
        match = VERDICT_PATTERN.search(block)
        if match is not None:
            return {"verdict": match.group(1)}

    raise ValueError("missing review verdict")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv if argv is None else argv
    try:
        text = _read_input(args)
        result = parse_review(text)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
