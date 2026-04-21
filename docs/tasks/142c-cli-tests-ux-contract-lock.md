# Task 142C — CLI tests UX contract lock (doctor 포함)

## Goal
Part 4 UX contract wording drift를 `tests/test_cli.py`에서 빠르게 실패시키도록 고정한다.

## Roadmap position
- Execution task for Part 4.

## Non-goals
- 런타임 동작 변경
- 광범위한 테스트 리팩터링

## Allowed files
- `docs/tasks/142c-cli-tests-ux-contract-lock.md`
- `tests/test_cli.py`

## Required changes
1) README/help contract assertions 업데이트:
   - first-run primary flow (`doctor -> setup -> agent new -> agent setup -> agent start`)
   - `doctor` infra-only wording
   - support surfaces(Portable state/visibility)의 secondary positioning
2) Positive/negative assertions 추가:
   - primary UX에서 `doctor` 누락/약화가 실패하도록
   - support surfaces가 primary bootstrap처럼 보이는 문구를 차단
3) 기존 Part 1~3 contract checks는 충돌 없는 범위에서 유지

## Acceptance criteria
- `tests/test_cli.py`에 Part 4 UX contract explicit assertions가 존재한다.
- 테스트가 green 상태를 유지한다.

## Validation
- `python3 -m pytest -q tests/test_cli.py`
