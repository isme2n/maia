# Task 081 — Final release-candidate verify and cleanup

## Goal
- Maia v1 RC를 위해 final verify, smoke, worktree cleanliness, and closeout wording을 마무리한다.

## Non-goals
- new features
- architectural scope expansion

## Allowed files
- `README.md`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `docs/plans/phase10-release-hardening-and-v1-closeout.md`

## Acceptance criteria
- [x] targeted tests green
- [x] `bash scripts/verify.sh` green
- [x] representative smoke sequence green
- [x] worktree clean at end
- [x] final docs/help wording aligns with RC state

## Closeout evidence
- Targeted tests passed:
  - `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
  - latest broader closeout validation covering the same RC surfaces passed as `164 passed`
- Full verify passed:
  - `cd /home/asle/maia && bash scripts/verify.sh`
  - latest result: `309 passed`
- Representative smoke passed:
  - fresh-home runtime bootstrap no longer requires `agent tune` for first start
  - live Hermes runtime + broker-backed request/reply succeeded
  - self-discovery smoke succeeded after rebuilding the local worker image from current source
- Docs/help alignment passed:
  - top-level help wording reflects the RC state
  - README/help/tests no longer encode the old hidden `agent tune` prerequisite
- Worktree cleanliness passed after scoped closeout commits

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `cd /home/asle/maia && bash scripts/verify.sh`

## Forbidden changes
- broad unrelated refactors
- runtime adapter expansion unless a real blocker is found
- broker adapter expansion
