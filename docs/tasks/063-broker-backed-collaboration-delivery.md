# Task 063 - broker-backed collaboration delivery wiring

## Goal
existing `send` / `reply` / `inbox` collaboration flow를 broker-backed live delivery path와 연결한다.

## Non-goals
- daemonized consumer loop
- complete history migration
- alternate brokers 추가

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py` (필요 시 최소 flag 추가)
- `src/maia/collaboration_storage.py`
- `src/maia/rabbitmq_broker.py`
- `src/maia/app_state.py` (broker config path helper가 필요할 때만)
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `tests/test_rabbitmq_broker.py`

## Acceptance criteria
- [ ] `send` / `reply`는 thread/message metadata를 기존 storage에 남기면서 live delivery는 broker publish를 사용한다.
- [ ] `inbox`는 broker pull 결과를 operator-friendly 출력으로 보여준다.
- [ ] broker가 비활성/미설정일 때 fallback/error policy가 명확하다.
- [ ] thread model과 single-target `to_agent` 규칙이 유지된다.
- [ ] targeted tests가 fake/stub broker 또는 local RabbitMQ로 green이다.

## Required validation commands
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_rabbitmq_broker.py`

## Forbidden changes
- top-level CLI verb churn
- thread/message public model 재설계
- unrelated portable-state 수정
