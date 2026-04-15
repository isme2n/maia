# Task 017 — portable state scope definition

## Goal
Define the boundary between portable Maia state and runtime-only Maia state, and encode that boundary directly in the backup manifest.

## Why now
- `maia export` / `maia import` are now the canonical public state-transfer commands.
- The remaining ambiguity is not the command name, but the payload scope.
- If scope is not recorded explicitly now, future additions risk turning export/import into an accidental dump of mixed durable and ephemeral state.

## Scope
- Extend `manifest.json` with explicit portable-scope metadata.
- Record both:
  - portable state kinds
  - runtime-only state kinds
- Document the current v1 boundary in README.

## Non-goals
- No expansion of exported payload beyond the current registry bundle.
- No process checkpointing or live runtime resurrection.
- No Docker / DB / queue migration yet.

## Scope definition v1

Portable state kinds:
- `registry`

Runtime-only state kinds:
- `processes`
- `locks`
- `cache`
- `live-sessions`

Manifest additions:

```json
{
  "scope_version": 1,
  "portable_state_kinds": ["registry"],
  "runtime_only_state_kinds": [
    "processes",
    "locks",
    "cache",
    "live-sessions"
  ]
}
```

## Rationale
- `registry` is portable because it is declarative state required to reconstruct Maia's current team configuration.
- `processes`, `locks`, `cache`, and `live-sessions` are runtime-only because they are ephemeral execution details that should be regenerated in a new environment.

## Files to modify
- `src/maia/backup_manifest.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- `maia export` writes a manifest containing `scope_version`, `portable_state_kinds`, and `runtime_only_state_kinds`.
- `maia import` validates those new manifest fields.
- Invalid manifests that classify `registry` as runtime-only fail with a clear error.
- README explains the current portable/runtime boundary.

## Validation
- `python3 -m pytest -q tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`