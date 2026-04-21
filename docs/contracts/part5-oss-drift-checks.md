# Part 5 OSS Drift Checks

Run from the repo root. The help checks below use the module-entrypoint form (`python3 -m maia`). If the current interpreter does not resolve `maia`, rerun in an environment where Maia is installed or importable (for example `PYTHONPATH=src`).

This file defines the Part 5 target baseline. The README and contributor-doc checks are expected to pass after 143B and 143C land. They are written now so later doc cleanup work has a fixed, executable target instead of ad hoc review comments.

## README First-Screen Checks

```bash
# README first screen should read like a product landing page, not a task log.
python3 - <<'PY'
from pathlib import Path

top = "\n".join(Path("README.md").read_text(encoding="utf-8").splitlines()[:140]).lower()

required_groups = [
    ("install",),
    ("quickstart", "first run"),
    ("control plane",),
    ("keryx", "collaboration"),
    ("/keryx",),
]
for group in required_groups:
    if not any(token in top for token in group):
        raise SystemExit(f"missing README first-screen concept group: {group}")

bootstrap_steps = [
    "maia doctor",
    "maia setup",
    "maia agent new",
    "maia agent setup",
    "maia agent start",
]
positions = []
for step in bootstrap_steps:
    index = top.find(step)
    if index == -1:
        raise SystemExit(f"missing README quickstart step: {step}")
    positions.append(index)
if positions != sorted(positions):
    raise SystemExit("README quickstart steps drifted out of order")

banned = [
    "structured marker block",
    "codex-parse-review.py",
    "watch policy",
    "reviewer approval is read from",
    "docs/tasks/",
]
for token in banned:
    if token in top:
        raise SystemExit(f"README first screen leaked internal detail: {token}")
PY

# Part 1 bootstrap stays present in README without requiring line-exact wording.
rg -n 'maia doctor' README.md
rg -n 'maia setup' README.md
rg -n 'maia agent new' README.md
rg -n 'maia agent setup <name>|maia agent setup [a-zA-Z0-9_-]+' README.md
rg -n 'maia agent start <name>|maia agent start [a-zA-Z0-9_-]+' README.md

# Part 2 Keryx concept stays visible in README.
rg -n '/keryx <instruction>|/keryx ' README.md
rg -n 'control plane' README.md
rg -n 'keryx.*collaboration|collaboration.*keryx' -i README.md

# Support surfaces stay present, but not as the primary bootstrap story.
rg -n -i '\bexport\b' README.md
rg -n -i '\bimport\b' README.md
rg -n -i '\binspect\b' README.md
rg -n -i '\bthread\b' README.md
rg -n -i '\bhandoff\b' README.md
rg -n -i '\bworkspace\b' README.md
if sed -n '1,140p' README.md | rg -i 'development notes|registry persistence|harness watch|review parser'; then
  echo 'README first screen drifted back toward contributor/internal detail'
  exit 1
fi
```

## Contributor-Doc Split Checks

```bash
# These files are the Part 5 contributor-facing split target.
test -f CONTRIBUTING.md
test -f TESTING.md
test -f ARCHITECTURE.md

# README should link out to contributor docs instead of inlining their detail.
rg -n 'CONTRIBUTING\.md' README.md
rg -n 'TESTING\.md' README.md
rg -n 'ARCHITECTURE\.md' README.md

# Each contributor doc keeps a distinct role.
rg -n -i 'development environment|local setup' CONTRIBUTING.md
rg -n -i '\bworker\b' CONTRIBUTING.md
rg -n -i '\breviewer\b' CONTRIBUTING.md
rg -n -i '\bverify\b|validation' CONTRIBUTING.md
rg -n -i 'pull request|commit' CONTRIBUTING.md
rg -n -i 'pytest' TESTING.md
rg -n -i '\bquick\b' TESTING.md
rg -n -i '\bfocused\b' TESTING.md
rg -n -i '\bfull\b' TESTING.md
rg -n -i '\bdebug\b' TESTING.md
rg -n -i 'control plane' ARCHITECTURE.md
rg -n -i 'collaboration plane' ARCHITECTURE.md
rg -n -i '\bmodule\b' ARCHITECTURE.md
rg -n -i '\bcli\b' ARCHITECTURE.md
rg -n -i '\bkeryx\b' ARCHITECTURE.md

# README first screen must not carry the detailed contributor workflow after the split.
if sed -n '1,140p' README.md | rg -i 'worker codex|reviewer codex|verify loop|pytest -q tests/test_cli.py tests/test_cli_runtime.py'; then
  echo 'README first screen still contains contributor-doc detail'
  exit 1
fi
```

## Top-Level Help Sanity Checks

```bash
main_help="$(python3 -m maia --help)"
printf '%s\n' "$main_help" | rg -n 'Part 1 operator flow'
printf '%s\n' "$main_help" | rg -n 'Portable state flow'
printf '%s\n' "$main_help" | rg -n 'Support surfaces'
printf '%s\n' "$main_help" | rg -n 'Keryx collaboration contract'
printf '%s\n' "$main_help" | rg -n 'maia doctor'
printf '%s\n' "$main_help" | rg -n 'maia setup'
printf '%s\n' "$main_help" | rg -n 'maia agent new'
printf '%s\n' "$main_help" | rg -n 'maia agent setup (planner|<name>|[A-Za-z0-9_-]+)'
printf '%s\n' "$main_help" | rg -n 'maia agent start (planner|<name>|[A-Za-z0-9_-]+)'
printf '%s\n' "$main_help" | rg -n '/keryx <instruction>|/keryx '
printf '%s\n' "$main_help" | rg -n 'thread_id'
printf '%s\n' "$main_help" | rg -n 'delivery_mode'
if printf '%s\n' "$main_help" | rg -i 'CONTRIBUTING|TESTING|ARCHITECTURE|watch policy|structured marker block'; then
  echo 'top-level help drifted into contributor/internal narrative'
  exit 1
fi

doctor_help="$(python3 -m maia doctor --help)"
printf '%s\n' "$doctor_help" | rg -n 'Docker, queue, and DB'
if printf '%s\n' "$doctor_help" | rg -i 'provider|login|model'; then
  echo 'doctor help drifted beyond the shared-infra scope'
  exit 1
fi

agent_help="$(python3 -m maia agent --help)"
printf '%s\n' "$agent_help" | rg -n 'Create an agent identity'
printf '%s\n' "$agent_help" | rg -n 'Open hermes setup'
printf '%s\n' "$agent_help" | rg -n 'Reopen hermes setup gateway'
printf '%s\n' "$agent_help" | rg -n 'Start an agent runtime'
```

## Focused Pytest Checks

```bash
python3 -m pytest -q \
  tests/test_cli.py::test_readme_locks_part1_public_flow \
  tests/test_cli.py::test_readme_locks_direct_agent_anchor_story \
  tests/test_cli.py::test_top_level_help \
  tests/test_cli.py::test_doctor_help_includes_examples \
  tests/test_cli.py::test_setup_help_includes_examples \
  tests/test_cli.py::test_agent_new_help_describes_identity_only_flow \
  tests/test_cli.py::test_agent_setup_help_includes_examples \
  tests/test_cli.py::test_agent_runtime_help_uses_operator_wording \
  tests/test_cli.py::test_agent_start_help_describes_part1_prerequisites \
  tests/test_cli.py::test_thread_help_includes_examples \
  tests/test_cli.py::test_collaboration_help_centers_keryx_visibility_surface \
  tests/test_cli.py::test_import_help_describes_safety_flags \
  tests/test_cli.py::test_inspect_help_includes_examples \
  tests/test_cli.py::test_export_help_includes_examples \
  tests/test_cli.py::test_readme_examples_align_with_public_help
```

## Full Validation

```bash
python3 -m pytest -q tests/test_cli.py
```
