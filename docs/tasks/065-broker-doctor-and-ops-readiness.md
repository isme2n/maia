# Task 065 - broker doctor and ops readiness

## Goal
실제 broker 운영에 필요한 host/container readiness를 `doctor`와 운영 문서에 반영해서, Docker green과 broker green을 구분 가능하게 만든다.

## Non-goals
- full installer automation
- production deployment guide 완성

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py` (필요 시 help text만)
- `README.md` (최소 수정)
- `docs/plans/phase6-real-broker-integration.md`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`

## Acceptance criteria
- [ ] `doctor`가 Docker readiness와 broker readiness를 분리해서 보고한다.
- [ ] RabbitMQ container/service 연결 실패 원인이 operator-friendly remediation으로 출력된다.
- [ ] README/help text가 현재 범위(실 broker 필요 여부)를 과장 없이 설명한다.
- [ ] live smoke validation 절차가 문서화된다.

## Required validation commands
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`

## Forbidden changes
- unrelated README cleanup
- phase 7 범위 선반영
