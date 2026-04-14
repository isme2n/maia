#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

printf '\n[verify] repo: %s\n' "$ROOT"

if command -v python3 >/dev/null 2>&1; then
  if [ -d tests ]; then
    printf '[verify] pytest\n'
    python3 -m pytest -q
  else
    printf '[verify] tests directory not found, skipping pytest\n'
  fi
else
  printf '[verify] python3 not found, skipping python checks\n'
fi

printf '[verify] done\n'
