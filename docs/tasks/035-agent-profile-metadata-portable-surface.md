# Task 035 — agent profile metadata portable surface

## Goal
Implement the second portable-state slice by making agent profile metadata first-class in the Maia registry, CLI surface, import/export contract, and inspect output.

## Scope
Portable agent profile metadata added in this slice:
- `role`
- `model`
- `tags`

## Approach
- Extend `AgentRecord` with `role`, `model`, and `tags` while keeping backward compatibility for older registry snapshots that only contain `agent_id`, `name`, `status`, and `persona`.
- Extend `maia agent tune` so operators can update persona plus profile metadata in one command.
- Keep `agent list` compact, but expand `agent status` to print persona/profile fields.
- Expand import preview change details so portable profile changes appear before apply.
- Expand inspect output with a compact per-agent `profiles` summary line.
- Bump manifest scope to `scope_version=3` and add `agent-profile-metadata` to `portable_state_kinds`.
- Continue loading older `scope_version=1` and `scope_version=2` manifests.

## CLI shape
### Tune
Supported flags:
- `--persona <text>`
- `--persona-file <path>`
- `--role <text>` / `--clear-role`
- `--model <text>` / `--clear-model`
- `--tags <comma,separated,list>` / `--clear-tags`

Validation rules:
- At least one change flag is required.
- Conflicting setter/clearer pairs are rejected by the parser.
- `role` and `model` reject whitespace-only values.
- `tags` must be a comma-separated list of non-empty values.
- Duplicate tags collapse to first-seen unique order.

## Acceptance criteria
- New agent records persist empty `role`, `model`, and `tags` by default.
- `agent tune` can update and clear profile metadata without affecting agent identity or lifecycle state.
- `agent status` prints persona, role, model, and tags.
- Export/import preserve role/model/tags.
- Import preview change details include role/model/tags when they differ.
- Inspect prints a `profiles` summary line for imported snapshots.
- New manifests write `scope_version=3` with `portable_state_kinds=["registry", "team-metadata", "agent-profile-metadata"]`.
- Older `scope_version=1` and `scope_version=2` manifests still load.

## Files touched
- `src/maia/agent_model.py`
- `src/maia/registry.py`
- `src/maia/cli.py`
- `src/maia/backup_manifest.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
