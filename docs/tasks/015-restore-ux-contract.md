# Task 015 — restore UX contract

## Goal
Experiment with a dedicated portable-restore CLI workflow instead of relying only on the lower-level `import` command.

## Why now
- Task 014 established a bundle contract with `manifest.json` + `registry.json`.
- The next usability step is to make restore intent explicit in the CLI.
- This reduces ambiguity between:
  - low-level data import, and
  - operator-facing bundle restore.

## Scope
- Add a dedicated agent-scoped portable-restore command using a manifest path.
- Keep `maia agent import <path>` working for compatibility.
- Require a manifest path explicitly.
- Reuse the existing bundle validation and registry loading path.

## Non-goals
- No change to lifecycle `maia agent restore <id>`.
- No new bundle contents beyond manifest + registry.
- No merge/preview/dry-run restore.

## Contract
- The dedicated restore command only accepts `manifest.json` paths.
- On success it prints:

```text
restored source=<manifest> registry=<registry> agents=<count>
```

- If a raw registry JSON path is passed, Maia returns a clear error instead of silently treating it as a generic import.

## Files to modify
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- The dedicated restore command restores successfully from a manifest path.
- Passing a raw registry path fails with a clear manifest-required error.
- The direct placeholder contract remains intact.
- Existing `import` behavior remains intact.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- Manual runtime flow:
  - `PYTHONPATH=src python3 -m maia agent export`
  - `PYTHONPATH=src python3 -m maia agent <dedicated-restore-command> ~/.maia/exports/manifest.json`