# Task 077 — Final golden-flow UX alignment and cleanup

## Goal
- Phase 9 기준 public UX, examples, and tests를 최종 정렬해서 v1 operator flow를 흔들림 없이 고정한다.

## Non-goals
- new product surfaces
- release documentation full closeout

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] top-level help, command help, README examples, tests가 같은 flow를 가리킨다.
- [ ] public help에 obsolete wording이나 phase-mismatched 예시가 남지 않는다.
- [ ] `bash scripts/verify.sh`까지 green 유지 준비가 된다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `cd /home/asle/maia && bash scripts/verify.sh`

## Forbidden changes
- runtime adapter files
- broker adapter files
- import/export files
