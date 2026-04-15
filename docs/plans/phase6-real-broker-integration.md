# Phase 6 Real Broker Integration Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia의 collaboration surface를 로컬 JSON 저장만이 아니라 실제 broker-backed message plane까지 확장해서, 실행 중인 에이전트들이 thread/message 모델을 유지한 채 inbox/outbox 전달을 할 수 있게 만든다.

**Architecture:** Maia는 계속 control plane으로 남고, live delivery는 별도 broker transport가 맡는다. public model은 여전히 `ThreadRecord` / `MessageRecord` / `HandoffRecord` 중심이고, broker는 delivery/ack/retry를 담당하는 transport layer로 붙는다. Phase 6은 RabbitMQ를 첫 실제 adapter로 도입하되, existing local collaboration storage를 바로 지우지 않고 thread metadata/history와 live inbox delivery를 분리해서 점진 전환한다.

**Tech Stack:** Python stdlib, existing Maia broker/message/runtime modules, RabbitMQ (Docker-backed for local ops), pytest.

---

## Scope
- RabbitMQ-backed real broker adapter 추가
- broker readiness/connection doctor 확장
- CLI collaboration path를 broker-backed delivery로 확장
- inbox ack/read semantics의 첫 운영형 contract 정리

## Out of scope
- always-on Maia daemon
- multi-recipient routing
- advanced retry/dead-letter policy
- agent SDK / in-container auto-consumer loop
- PostgreSQL registry migration

## Ground rules
- control plane와 live transport를 분리 유지한다.
- public collaboration model은 `MessageRecord` / `ThreadRecord` 중심을 유지한다.
- broker는 transport detail이고, Maia CLI surface는 agent/thread/message 중심을 유지한다.
- local JSON collaboration state는 thread metadata/history fallback으로 유지하되, live delivery path와 역할을 명확히 나눈다.

## Task breakdown
1. Task 062 — RabbitMQ runtime and broker adapter foundation
2. Task 063 — broker-backed collaboration delivery wiring
3. Task 064 — inbox ack semantics and operator-safe pull flow
4. Task 065 — doctor/readiness/runtime docs for real broker ops

## Verification bar
- task별 targeted pytest
- RabbitMQ container 기반 local smoke validation
- `bash scripts/verify.sh`
- reviewer approve
- 기능 묶음 단위 selective commit
