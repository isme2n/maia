# Task 059 - doctor remediation UX hardening

## Goal
`maia doctor`가 단순 fail/pass를 넘어서 operator가 다음에 무엇을 해야 하는지 안내한다.

## Non-goals
- package installer 실행
- privileged host mutation

## Allowed files
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`

## Acceptance criteria
- [ ] missing/fail 상태별 remediation hint를 출력한다.
- [ ] host에 docker가 없을 때 next step이 명확하다.
- [ ] one-line key=value output contract를 유지한다.

## Required validation commands
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- doctor를 interactive installer로 바꾸기
