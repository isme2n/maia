# Task 078 — Failure-mode and error-message hardening

## Goal
- Maia v1에서 operator가 자주 마주치는 실패 모드를 clear error/fallback 정책으로 고정한다.

## Non-goals
- new commands
- architectural expansion

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] missing/malformed state, missing runtime spec/workspace, stale runtime, and handoff/workspace edge cases가 clear operator-facing behavior로 고정된다.
- [ ] error wording이 일관된다.
- [ ] targeted failure-mode tests가 추가된다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- runtime adapter files unless verify reveals a true blocker
- broker adapter files
- export/import manifests
