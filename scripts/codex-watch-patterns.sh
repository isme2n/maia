#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: scripts/codex-watch-patterns.sh <worker|reviewer>" >&2
  exit 1
fi

role="$1"

case "$role" in
  worker)
    cat <<'EOF'
^Traceback \(most recent call last\):$
^FAILED .*$
^AssertionError(:|$)
EOF
    ;;
  reviewer)
    cat <<'EOF'
^Traceback \(most recent call last\):$
^AssertionError(:|$)
EOF
    ;;
  *)
    echo "error: unknown role '$role' (expected worker or reviewer)" >&2
    exit 1
    ;;
esac
