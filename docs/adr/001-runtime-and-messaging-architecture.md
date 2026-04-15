# ADR-001: Maia runtime and messaging architecture

## Status
Accepted

## Context
Maia는 멀티 Hermes 에이전트를 운영하는 control plane이다. 핵심 요구는 다음과 같다.
- agent 생성/관리
- Docker runtime 제어
- agent-to-agent multi-turn messaging
- 중간 질문/답변/보고
- artifact/workspace handoff
- Maia 자체는 가능하면 상시 central bus가 아니어야 함

OpenClaw의 sessions_send는 참고 가치가 있다. 하지만 Maia는 session-centric product가 아니라 agent-centric product여야 하며, 중앙 gateway가 모든 live traffic을 직접 중계하는 구조보다 control plane / message plane 분리가 더 적합하다.

## Decision
Maia는 다음 4-plane 구조를 채택한다.

1. Control plane
- Maia CLI
- agent registry
- team metadata
- routing policy metadata
- transfer/import/export/inspect

2. Runtime plane
- Docker / Docker Compose
- agent container lifecycle
- container status / logs / heartbeat

3. Message plane
- RabbitMQ를 기본 broker로 사용
- running agent는 broker에 직접 연결
- Maia는 live message transport를 직접 중계하지 않음

4. Workspace / artifact plane
- shared workspace or artifact store
- thread와 artifact를 연결 가능한 metadata 보유

## Consequences
### Positive
- Maia를 lightweight control plane으로 유지 가능
- multi-turn messaging을 broker 기반으로 안정적으로 처리 가능
- agent inbox/outbox 모델이 명확함
- runtime과 messaging 책임이 분리됨
- 향후 presence, retry, buffering 확장이 쉬움

### Negative
- 초기 구성요소가 늘어남 (broker + registry + runtime)
- thread metadata와 broker transport를 따로 설계해야 함
- 단일 central gateway보다 구현 포인트가 조금 많음

## Rejected alternatives
### 1. Maia-as-bus
Maia가 모든 live message를 직접 받고 라우팅하는 방식은 rejected.
이유:
- Maia가 상시 핵심 데몬이 됨
- control plane과 message plane이 과도하게 결합됨
- broker가 잘하는 책임을 Maia가 다시 갖게 됨

### 2. One-shot task queue first
단발성 job queue 중심 모델은 rejected.
이유:
- multi-turn question/answer/report를 충분히 설명하지 못함
- 협업 thread가 제품 중심 개념이어야 함

### 3. Session-first public model
OpenClaw처럼 session key 중심 public model은 rejected.
이유:
- Maia의 operator mental model은 agent/team 중심임
- session/thread는 agent 활동 단위로 뒤에 와야 함

## Transport choice
Current default: RabbitMQ

Why RabbitMQ first:
- inbox/outbox mental model에 잘 맞음
- routing key / queue / ack / buffering이 명확함
- long-lived multi-agent collaboration transport에 적합함

Redis Streams is allowed as a future alternative, but not the baseline design target.

## Domain model priority order
1. Agent
2. Thread
3. Message
4. Artifact
5. Presence
6. Task metadata (optional, derived or supplemental)

## Command contract implications
- `maia agent new/start/stop/status`는 runtime semantics로 수렴해야 한다.
- `maia send/reply/inbox/thread`는 thread/message semantics를 기준으로 설계한다.
- transfer commands (`export/import/inspect`)는 top-level에 남긴다.

## Implementation note
현재 코드베이스는 registry/export/import 중심이다. 다음 단계 구현은 기존 portable-state foundation을 유지하면서 아래 순서로 확장한다.
1. runtime spec 모델 추가
2. broker-backed message/thread 모델 추가
3. Docker lifecycle 연결
4. artifact/workspace handoff 메타데이터 추가
