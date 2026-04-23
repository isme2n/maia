#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)

DOCKER_BIN=${DOCKER_BIN:-docker}
BASE_IMAGE=${BASE_IMAGE:-maia-local/hermes-worker:latest}
TARGET_IMAGE=${TARGET_IMAGE:-maia-local/hermes-worker:latest}
CHECK_ONLY=0
ALLOW_DIRTY=${ALLOW_DIRTY:-0}

usage() {
  cat <<'USAGE'
Usage: scripts/rebuild-runtime-worker-image.sh [--check]

Rebuild the local Maia runtime worker image from the current source tree while
preserving the existing runtime base image environment.

Environment variables:
  DOCKER_BIN    Docker CLI to use (default: docker)
  BASE_IMAGE    Existing local base image to layer on top of
                (default: maia-local/hermes-worker:latest)
  TARGET_IMAGE  Output image tag (default: maia-local/hermes-worker:latest)
  ALLOW_DIRTY   Set to 1 to allow rebuilding from a dirty git tree

Modes:
  --check       Verify whether TARGET_IMAGE labels match the current git state.
USAGE
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command not found: $1" >&2
    exit 1
  fi
}

require_command git
require_command "$DOCKER_BIN"

if [[ $# -gt 1 ]]; then
  usage
  exit 2
fi

if [[ $# -eq 1 ]]; then
  case "$1" in
    --check)
      CHECK_ONLY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
fi

current_revision=$(git -C "$REPO_ROOT" rev-parse HEAD)
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain=v1 --untracked-files=normal)" ]]; then
  dirty=true
else
  dirty=false
fi

inspect_label() {
  local image=$1
  local label=$2
  "$DOCKER_BIN" image inspect --format "{{ index .Config.Labels \"$label\" }}" "$image"
}

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  if ! "$DOCKER_BIN" image inspect "$TARGET_IMAGE" >/dev/null 2>&1; then
    echo "stale: target image $TARGET_IMAGE does not exist"
    exit 1
  fi
  image_revision=$(inspect_label "$TARGET_IMAGE" "io.maia.runtime-source-revision")
  image_dirty=$(inspect_label "$TARGET_IMAGE" "io.maia.runtime-source-dirty")
  if [[ "$image_revision" == "$current_revision" && "$image_dirty" == "$dirty" ]]; then
    echo "fresh: $TARGET_IMAGE matches revision=$current_revision dirty=$dirty"
    exit 0
  fi
  echo "stale: $TARGET_IMAGE revision=$image_revision dirty=$image_dirty current_revision=$current_revision current_dirty=$dirty"
  exit 1
fi

if [[ "$dirty" == true && "$ALLOW_DIRTY" != "1" ]]; then
  echo "error: git tree is dirty. Commit or stash changes first, or rerun with ALLOW_DIRTY=1." >&2
  exit 1
fi

if ! "$DOCKER_BIN" image inspect "$BASE_IMAGE" >/dev/null 2>&1; then
  echo "error: base image $BASE_IMAGE was not found locally" >&2
  exit 1
fi

base_ref=$BASE_IMAGE
temp_base_tag=
cleanup() {
  if [[ -n "$temp_base_tag" ]]; then
    "$DOCKER_BIN" image rm -f "$temp_base_tag" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ "$BASE_IMAGE" == "$TARGET_IMAGE" ]]; then
  temp_base_tag="maia-local/hermes-worker:build-base-$$"
  "$DOCKER_BIN" image tag "$BASE_IMAGE" "$temp_base_tag"
  base_ref=$temp_base_tag
fi

built_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "building $TARGET_IMAGE from base=$base_ref revision=$current_revision dirty=$dirty"
"$DOCKER_BIN" build \
  --build-arg BASE_IMAGE="$base_ref" \
  --label "io.maia.runtime-source-revision=$current_revision" \
  --label "io.maia.runtime-source-dirty=$dirty" \
  --label "io.maia.runtime-built-at=$built_at" \
  -t "$TARGET_IMAGE" \
  -f - "$REPO_ROOT" <<'DOCKERFILE'
ARG BASE_IMAGE=maia-local/hermes-worker:latest
FROM ${BASE_IMAGE}

WORKDIR /opt/maia
COPY pyproject.toml README.md /opt/maia/
COPY src /opt/maia/src
RUN python -m pip install --no-cache-dir .
ENTRYPOINT ["python", "-m", "maia.hermes_runtime_worker"]
DOCKERFILE

image_revision=$(inspect_label "$TARGET_IMAGE" "io.maia.runtime-source-revision")
image_dirty=$(inspect_label "$TARGET_IMAGE" "io.maia.runtime-source-dirty")
image_built_at=$(inspect_label "$TARGET_IMAGE" "io.maia.runtime-built-at")

echo "built: $TARGET_IMAGE revision=$image_revision dirty=$image_dirty built_at=$image_built_at"
