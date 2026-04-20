# Task 137C - Legacy thread cleanup and closeout

## Goal
Close Task 137 by removing the remaining active legacy-thread contract surfaces and aligning docs/tests/state helpers around Keryx thread as the single active meaning of `thread`.

## Non-goals
- redesigning Keryx storage internals beyond what is needed to eliminate dual-meaning thread behavior
- touching unrelated runtime/bootstrap work
- changing Hermes session semantics

## Allowed files
- `docs/tasks/137c-legacy-thread-cleanup-and-closeout.md`
- `docs/tasks/137-keryx-thread-redefinition-after-legacy-purge.md`
- `README.md`
- `docs/prd/maia-core-product.md`
- `docs/plans/2026-04-20-keryx-migration-closeout.md`
- `src/maia/collaboration_storage.py`
- `src/maia/message_model.py`
- `src/maia/handoff_model.py`
- `src/maia/sqlite_state.py`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/agent_context.py`
- `tests/test_agent_context.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `tests/test_hermes_runtime_worker.py`
- `tests/test_sqlite_state.py`
- `tests/test_keryx_service.py`
- `tests/test_keryx_server.py`

## Acceptance criteria
- [x] no active code path or operator-facing docs/tests keeps two live meanings of `thread`.
- [x] any remaining legacy collaboration helper/model is clearly non-active or removed.
- [x] Task 137 acceptance checkboxes are all updated to complete.
- [x] final targeted validation passes.
- [x] live help output matches the new Keryx thread contract.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_agent_context.py tests/test_cli.py tests/test_cli_runtime.py tests/test_hermes_runtime_worker.py tests/test_keryx_service.py tests/test_keryx_server.py tests/test_sqlite_state.py`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia --help`
- `cd /home/asle/maia && PYTHONPATH=src python3 -m maia thread --help`
- `cd /home/asle/maia && HOME=/tmp/tmp.XMgdLzcroJ PYTHONPATH=src python3 -m maia thread show sess01`
- `cd /home/asle/maia && HOME=/tmp/tmp.XMgdLzcroJ PYTHONPATH=src python3 -m maia handoff show handoff01`

## Forbidden changes
- reopening legacy compatibility surfaces
- changing files outside the allowed scope
- leaving docs/help/tests with mixed `thread` and `session` public wording for the same Keryx object
