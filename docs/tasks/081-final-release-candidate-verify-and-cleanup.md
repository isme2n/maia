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
- [ ] targeted tests green
- [ ] `bash scripts/verify.sh` green
- [ ] representative smoke sequence green
- [ ] worktree clean at end
- [ ] final docs/help wording aligns with RC state

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `cd /home/asle/maia && bash scripts/verify.sh`

## Forbidden changes
- broad unrelated refactors
- runtime adapter expansion unless a real blocker is found
- broker adapter expansion
