#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/codex-review.sh <task-spec-path>"
  exit 1
fi

TASK_SPEC="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1

PROMPT=$(cat <<EOF
You are the reviewer Codex for the Maia project.
Review the current uncommitted changes against this task spec: $TASK_SPEC

Rules:
- Do not implement the fix.
- Focus on requirement mismatch, regression risk, missing validation, and unsafe scope expansion.
- First inspect the task spec, current git diff, and verification-relevant files.
- Return the final review inside an exact marker block so tooling can parse it.
- The marker block format must be:
  REVIEW_RESULT_START
  verdict: approve | request_changes
  blocking_issues:
  - ...
  non_blocking_suggestions:
  - ...
  touched_risks:
  - ...
  summary: ...
  REVIEW_RESULT_END
- Do not omit the markers.
EOF
)

codex exec -p reviewer --dangerously-bypass-approvals-and-sandbox "$PROMPT"
