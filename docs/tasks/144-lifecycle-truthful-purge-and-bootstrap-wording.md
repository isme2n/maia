# Task 144 — lifecycle truthful purge and bootstrap wording

## Goal
Lock Maia's archive/purge lifecycle to truthful operator semantics, add bulk archive/purge commands if missing, make single-agent purge a true full delete, and align import/gateway/workspace wording with the actual product contract.

## Non-goals
- No roadmap updates in this task.
- No broad runtime architecture changes.
- No changes to Keryx storage/model behavior.
- No new merge/additive import mode.

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`
- `docs/prd/maia-core-product.md`
- `docs/tasks/144-lifecycle-truthful-purge-and-bootstrap-wording.md`

## Required behavior
1. `maia agent archive <id>` must not produce a lying state for running agents.
   - Preferred contract: refuse archive while runtime is active and tell the operator to stop first.
2. `maia agent purge <id>` must be a true full delete.
   - It must only work for archived agents.
   - It must remove registry entry, runtime state, default-agent pointer if needed, and the per-agent Maia/Hermes on-disk home.
3. Add bulk commands if they do not already exist:
   - `maia agent archive-all`
   - `maia agent purge-all`
4. Bulk-command contract:
   - `archive-all` must be all-or-nothing and must not silently archive running agents.
   - `purge-all` must be all-or-nothing, require archived agents only, and require explicit confirmation via `--yes`.
5. Import contract:
   - Keep import as snapshot replacement, not additive merge.
   - `import --preview` and the destructive apply path must explicitly warn that runtime/setup state is reset.
6. Gateway contract:
   - Gateway readiness is required for `agent start`.
   - `agent setup-gateway` is a recovery command when gateway setup was skipped during normal `agent setup`, not a separate primary bootstrap step.
7. Workspace wording:
   - Keep `workspace` as an operator support surface showing an agent participant's runtime/workspace context for collaboration follow-up.
   - Avoid implementation-leaking wording like "stored runtime spec" in public help/README/PRD surfaces.

## Acceptance criteria
- [x] New/updated tests fail first and then pass.
- [x] Archive no longer allows a running agent to become misleadingly archived.
- [x] Purge fully deletes the per-agent on-disk Hermes home.
- [x] `archive-all` and `purge-all --yes` exist and are covered by tests.
- [x] Import preview/apply output explicitly warns about runtime/setup reset.
- [x] CLI help / README / PRD align on gateway recovery wording and workspace wording.

## Required validation commands
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py -k 'archive or purge or import_clears_runtime_state_even_for_surviving_agent_ids'`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py -k 'workspace or setup_gateway or purge or archive or gateway_readiness'`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `PYTHONPATH=src python3 -m maia agent --help`
- `PYTHONPATH=src python3 -m maia agent start --help`
- `PYTHONPATH=src python3 -m maia workspace --help`

## Closeout evidence
- Focused runtime validation: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py -k 'archive or purge or import_clears_runtime_state_even_for_surviving_agent_ids'` → `7 passed`
- Focused help/contract validation: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py -k 'workspace or setup_gateway or purge or archive or gateway_readiness'` → `6 passed`
- Scoped regression validation: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py` → `131 passed`
- Live help checks rerun:
  - `PYTHONPATH=src python3 -m maia agent --help`
  - `PYTHONPATH=src python3 -m maia agent start --help`
  - `PYTHONPATH=src python3 -m maia workspace --help`
- Scoped reviewer verdict: `approve`

## Forbidden changes
- No unrelated refactors.
- No changes outside the allowed files.
- Do not reintroduce `/call`, `/agent-call`, or `artifact` wording.
- Do not turn import into a merge/additive operation in this task.
