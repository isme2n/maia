# Task 075 — Integrated collaboration lifecycle regression suite

## Goal
- messaging, handoff, workspace, status, logs 흐름이 분절되지 않도록 통합 회귀 테스트를 강화한다.

## Non-goals
- 새 command 추가
- transport architecture 변경

## Allowed files
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] send/reply/handoff/thread/workspace/status/logs를 한 흐름으로 묶은 regression coverage가 있다.
- [ ] stale/malformed runtime or collaboration 상태에서도 golden flow가 어디서 깨지는지 clear하게 드러난다.
- [ ] public output contract가 테스트로 고정된다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

## Forbidden changes
- runtime adapter files
- broker adapter files
- parser-wide command churn beyond tested flow needs
