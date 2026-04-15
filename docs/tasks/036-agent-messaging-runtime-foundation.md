# Task 036 - Agent messaging runtime foundation

## Goal
Maia를 registry/import-export 중심 상태에서, 실제 agent runtime + broker-backed multi-turn messaging foundation을 갖춘 구조로 진입시킨다.

## Why now
- 제품 핵심은 agent-to-agent collaboration이다.
- current code는 registry/status/export/import는 있으나 live runtime/message plane이 없다.
- 다음 구현은 public CLI contract를 유지하면서 runtime과 messaging core를 추가해야 한다.

## Scope
- runtime spec 도메인 모델 추가
- thread/message/artifact/presence 도메인 모델 추가
- RabbitMQ transport contract 초안 구현
- Docker lifecycle adapter 초안 구현
- CLI surface용 parser/handler 자리 마련

## Non-goals
- full production broker deployment automation
- complete UI/dashboard
- automatic multi-agent planner graph
- advanced retry policy
- full artifact file copy implementation

## Required docs to follow
- `docs/prd/maia-core-product.md`
- `docs/adr/001-runtime-and-messaging-architecture.md`
- `AGENTS.md`
- `docs/harness-runbook.md`

## Allowed files
- `src/maia/agent_model.py`
- `src/maia/cli.py`
- `src/maia/registry.py`
- `src/maia/storage.py`
- `src/maia/` 내 신규 파일 추가 가능
- `tests/` 내 관련 테스트 추가 가능
- `README.md`

## Deliverables
1. runtime spec 모델
2. thread/message 모델
3. presence 모델
4. artifact reference 모델
5. broker adapter interface
6. docker runtime adapter interface
7. 최소 CLI contract skeleton for send/inbox/thread

## Acceptance criteria
- [ ] agent 모델이 runtime/messaging 확장 가능 구조를 가진다.
- [ ] thread/message domain model이 정의된다.
- [ ] message에 `thread_id`, `from_agent`, `to_agent`, `kind`, `body`, `reply_to_message_id`가 있다.
- [ ] artifact reference model이 정의된다.
- [ ] presence/runtime status model이 정의된다.
- [ ] RabbitMQ transport adapter interface가 생긴다.
- [ ] Docker runtime adapter interface가 생긴다.
- [ ] CLI에 future runtime/messaging contract를 위한 명령 구조가 추가되거나 명확히 준비된다.
- [ ] 테스트가 새 도메인 모델/validation을 커버한다.

## Suggested file additions
- `src/maia/runtime_spec.py`
- `src/maia/message_model.py`
- `src/maia/artifact_model.py`
- `src/maia/presence_model.py`
- `src/maia/broker.py`
- `src/maia/runtime_adapter.py`
- `tests/test_message_model.py`
- `tests/test_runtime_spec.py`
- `tests/test_broker_contract.py`

## Validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`
- `PYTHONPATH=src python3 -m maia --help`

## Notes
- 현재 public lifecycle verbs (`new`, `start`, `stop`)는 유지한다.
- help/output/docs는 실제 구현 상태를 과장하지 않는다.
- queue/broker는 transport이고, public model은 thread/message 중심이다.
- Maia는 live traffic central bus가 아니라 control plane으로 유지한다.
