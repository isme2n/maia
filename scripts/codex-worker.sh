#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/codex-worker.sh <task-spec-path>"
  exit 1
fi

TASK_SPEC="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1

PROMPT=$(cat <<EOF
You are the worker Codex for the Maia project.

Read the task spec at: $TASK_SPEC
Rules:
- Implement only what the task asks.
- Do not change files outside the allowed scope.
- Run the required validation commands after changes.
- At the end, print:
  1. changed files
  2. validation commands run
  3. remaining risks
EOF
)

codex exec -p worker --dangerously-bypass-approvals-and-sandbox "$PROMPT"
