#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/codex-plan.sh <request-file-or-brief>"
  exit 1
fi

INPUT="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROMPT=$(cat <<EOF
You are the planner Codex for the Maia project.

Your job is to turn the input brief into a small, concrete task spec that a worker Codex can implement safely.

Input reference: $INPUT

Requirements:
- Break the work into the smallest useful slice.
- Include goal, non-goals, allowed files, acceptance criteria, required validation commands, forbidden changes.
- Prefer editing only a few files.
- Do not implement code changes.
- Output concise markdown suitable for docs/tasks/<slug>.md.
EOF
)

codex exec -p worker "$PROMPT"
