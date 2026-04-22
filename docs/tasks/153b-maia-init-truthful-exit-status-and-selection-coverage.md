# Task 153B — Maia init truthful exit status and selection coverage

## Goal
- Fix Task 153 reviewer blockers so `maia init` does not report process success for non-conversation-ready states.
- Add focused coverage for the truthful exit-status contract and the missing selection/transition branches noted in review.

## Reviewer blockers to address
- `_handle_init()` currently returns `0` even when `conversation_ready=no` and only a remediation step is available.
- Tests currently bless that incorrect success exit code for non-ready states.

## Non-goals
- Full init orchestration
- Gateway/runtime implementation changes beyond truthful surface behavior
- README/packaging contract changes

## Allowed files
- `src/maia/cli.py`
- `tests/test_cli.py`
- `docs/tasks/153b-maia-init-truthful-exit-status-and-selection-coverage.md`

## Acceptance criteria
- [ ] `maia init` returns success only when conversation-ready is true.
- [ ] Non-ready init states return non-zero while still printing truthful state and next-step lines.
- [ ] Tests are updated so non-ready init scenarios assert non-zero exit status.
- [ ] Add focused coverage for at least one runtime transitional branch (`starting` or `stopping`) and one default-agent selection branch.
- [ ] Focused pytest passes.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- No edits outside allowed files
- No README/help/pyproject changes in this task
- No new gateway/runtime orchestration logic

## Notes
- Keep the state output stable; this task is about truthful exit semantics and missing branch coverage.
