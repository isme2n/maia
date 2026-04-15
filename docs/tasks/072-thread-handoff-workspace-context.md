# Task 072 — Thread detail handoff and workspace context

## Goal
- `thread show`와 관련 handoff surface에서 operator가 handoff location과 workspace context를 함께 이해할 수 있게 만든다.

## Non-goals
- new thread state machine
- workspace file IO
- broker semantics 변경

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] `thread show <id>` summary 또는 detail에서 handoff count와 함께 recent handoff context가 보인다.
- [ ] handoff show에서 target/source agent workspace context를 operator-friendly 하게 보여준다.
- [ ] workspace 경로가 runtime spec 기준인지 명확히 드러난다.
- [ ] output wording은 handoff/workspace 중심이고 broker detail을 섞지 않는다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- collaboration storage schema
- runtime adapter implementation
- broker adapter implementation

## Notes
- 핵심 질문은 “이 handoff가 어느 workspace 쪽 결과물인가?”를 operator가 바로 이해하게 하는 것이다.
