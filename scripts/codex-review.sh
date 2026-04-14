#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/codex-review.sh <task-spec-path>"
  exit 1
fi

TASK_SPEC="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROMPT=$(cat <<EOF
You are the reviewer Codex for the Maia project.
Review the current uncommitted changes against this task spec: $TASK_SPEC

Rules:
- Do not implement the fix.
- Focus on requirement mismatch, regression risk, missing validation, and unsafe scope expansion.
- First inspect the task spec, current git diff, and verification-relevant files.
- Return a concise review with:
  verdict: approve | request_changes
  blocking_issues:
  non_blocking_suggestions:
  touched_risks:
  summary:
EOF
)

codex exec -p reviewer --dangerously-bypass-approvals-and-sandbox "$PROMPT"
