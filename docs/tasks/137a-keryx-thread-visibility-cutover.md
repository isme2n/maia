# Task 137A - Keryx thread visibility cutover

## Goal
Replace the active operator `thread` and `handoff` visibility path so it reads Keryx-backed collaboration state instead of the legacy `CollaborationStorage` thread model.

## Non-goals
- removing legacy collaboration tables from SQLite in this subtask
- changing Hermes runtime prompt/context wording yet
- broad docs/README/PRD sweeps beyond help text needed for this subtask

## Allowed files
- `docs/tasks/137a-keryx-thread-visibility-cutover.md`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/keryx_models.py`
- `src/maia/keryx_service.py`
- `tests/test_cli.py`

## Acceptance criteria
- [x] `maia thread list/show` reads Keryx-backed state, not `CollaborationStorage` / `ThreadRecord`.
- [x] `maia handoff show` can resolve a real Keryx handoff and include workspace context.
- [x] operator output uses `thread` / `thread_id` wording even if Keryx storage still uses `session_id` internally.
- [x] `tests/test_cli.py` thread/handoff assertions use Keryx fixtures/state rather than `ThreadRecord` / `MessageRecord` / `HandoffRecord`.
- [x] targeted validation passes, including live isolated-HOME repro commands.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia thread --help`
- `cd /home/asle/maia && HOME=/tmp/tmp.XMgdLzcroJ PYTHONPATH=src python3 -m maia thread show sess01`
- `cd /home/asle/maia && HOME=/tmp/tmp.XMgdLzcroJ PYTHONPATH=src python3 -m maia handoff show handoff01`

## Forbidden changes
- reintroducing a legacy fallback inside `maia thread`
- using bare `session` on the CLI/help output for the Keryx collaboration object
- modifying files outside the allowed scope
