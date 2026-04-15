# Task 080 — v1 release checklist and smoke checklist locking

## Goal
- Maia v1 release candidate를 판단하는 체크리스트와 smoke 순서를 문서/테스트 기준으로 고정한다.

## Non-goals
- new runtime or broker features
- release automation pipeline 구축

## Allowed files
- `README.md`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `docs/plans/phase10-release-hardening-and-v1-closeout.md`

## Acceptance criteria
- [ ] release checklist가 문서로 고정된다.
- [ ] smoke checklist가 실제 command sequence로 적힌다.
- [ ] help/README/examples와 checklist가 서로 모순되지 않는다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- runtime adapter files
- broker adapter files
- storage files
