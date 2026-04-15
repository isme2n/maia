# Task 026 — import risk classification

## Goal
Add an operator-friendly risk classification line to Maia import preview so an import can be judged at a glance before reading the full diff details.

## Why now
- The import flow already has preview, overwrite warnings, confirmation, and field-level before/after details.
- The remaining gap is quick triage: operators still need to infer whether a preview is a minor change, a destructive change, or effectively a team replacement.
- A compact risk line makes `maia import --preview`, `maia import`, and `maia import --yes` more legible during real operations.

## Scope
- Add a `risk ...` output line to import preview output.
- Compute a risk `level` and machine-readable `reasons` from the current/import snapshot comparison.
- Reuse the same classification for preview-only mode and destructive import preflight.
- Document the classification in the README.

## Non-goals
- No color output.
- No interactive TUI.
- No merge behavior.
- No probabilistic scoring.

## Classification contract
The new preview block gains a line immediately after the summary line:
- `risk level=<level> reasons=<reason-list>`

Levels:
- `safe`
  - no added, removed, or changed agents
- `low-change`
  - there is no destructive removal and the diff is small
  - also used when importing into an empty current registry because there is no overwrite loss
- `high-impact`
  - there is meaningful destructive or broad change, but the snapshots still share some identity overlap
- `replacement-like`
  - both sides are non-empty and there are zero shared agent ids, so the import behaves like replacing one Maia team with another

Reason tokens:
- `identical`
- `current_empty`
- `added_agents`
- `removed_agents`
- `changed_agents`
- `no_shared_agent_ids`

## Proposed rules
1. If there are no additions, removals, or changes:
   - `level=safe`
   - `reasons=identical`
2. Else if the current registry is empty:
   - `level=low-change`
   - include `current_empty` plus any additive reason tokens
3. Else if both current and incoming registries are non-empty and share zero agent ids:
   - `level=replacement-like`
   - include `no_shared_agent_ids`
4. Else if there are removed agents, or more than one changed agent, or more than one added agent:
   - `level=high-impact`
5. Else:
   - `level=low-change`

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- `maia import <path> --preview` prints a `risk` line.
- `maia import <path>` and `maia import <path> --yes` show the same risk line before applying an overwrite.
- Identical import previews classify as `safe`.
- Completely disjoint non-empty registries classify as `replacement-like`.
- Destructive overlapping changes classify as `high-impact`.
- Small additive changes classify as `low-change`.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
