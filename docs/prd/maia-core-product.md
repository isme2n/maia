# Maia Core Product PRD

## Product definition
Maia는 여러 Hermes 에이전트를 생성, 관리, 실행하고, 에이전트끼리 여러 번 왕복 대화하며 질문/답변/중간보고/작업물 전달을 할 수 있게 만드는 멀티 에이전트 운영용 control plane이다.

## Core principles
1. Maia의 1급 개념은 agent다.
2. 에이전트 협업의 1급 개념은 thread/message다.
3. Maia는 가능하면 상시 중앙 메시지 허브가 아니라 control plane으로 남는다.
4. 실시간 메시지 전달은 broker가 맡고, Maia는 정의/정책/관찰/운영을 맡는다.
5. UX와 DX는 운영 동사 중심으로 짧고 명확해야 한다.

## In scope (v1 foundation)
- agent 생성/조회/수정/삭제
- agent runtime spec 관리
- Docker 기반 start/stop/status/logs
- broker 기반 agent-to-agent messaging
- multi-turn thread/reply/report/question 흐름
- artifact/workspace handoff metadata
- import/export/inspect
- team metadata

## Out of scope (for now)
- Maia가 상시 central message bus 역할까지 직접 수행하는 구조
- 복잡한 planner graph / autonomous swarm arbitration
- multi-broker abstraction
- automatic self-healing daemon orchestration
- long-term knowledge sync between all agents

## User stories
1. 운영자는 `maia agent new tech`로 새 에이전트를 만든다.
2. 운영자는 `maia agent start tech`로 Docker runtime에 tech를 띄운다.
3. economy agent는 tech agent에게 구현 요청 메시지를 보낸다.
4. tech agent는 economy agent에게 추가 요구사항을 여러 번 질문한다.
5. tech agent는 economy workspace 또는 공유 artifact로 결과물을 넘긴다.
6. 운영자는 어떤 thread가 열려 있는지, 누가 답변 대기 중인지 본다.
7. 운영자는 팀 상태를 export/import로 안전하게 옮긴다.

## Canonical domain model
### Agent
- id
- name
- persona
- role
- model
- tags
- status
- runtime_spec
- messaging_spec

### Thread
- thread_id
- participants
- topic
- status
- created_at
- updated_at

### Message
- message_id
- thread_id
- from_agent
- to_agent
- kind (`request`, `question`, `answer`, `report`, `handoff`, `note`)
- body
- reply_to_message_id
- created_at

### Artifact
- artifact_id
- thread_id
- owner_agent
- target_agent
- type (`file`, `dir`, `repo-ref`, `report`, `link`)
- location
- summary
- created_at

### Presence
- agent_id
- runtime_status
- container_id
- last_heartbeat_at

## Architecture decision summary
- Control plane: Maia CLI + registry/metadata store
- Message plane: broker (RabbitMQ first)
- Runtime plane: Docker/Compose
- Workspace plane: shared workspace/artifact storage

## Why broker-backed messaging
- multi-turn 질문/답변/보고 흐름이 필요함
- offline agent backlog가 필요함
- direct inbox/outbox model이 필요함
- Maia를 상시 중앙 중계 데몬으로 만들고 싶지 않음

## Why not one-shot task queue only
단발성 job dispatch만으로는 아래를 충분히 설명하지 못한다.
- 중간 질문
- 진행 보고
- 여러 번 왕복되는 협업
- 노하우 전달
- artifact handoff 이후 후속 대화

## Public CLI direction
### Agent lifecycle
- `maia agent new <name>`
- `maia agent start <agent>`
- `maia agent stop <agent>`
- `maia agent status [agent]`
- `maia agent list`
- `maia agent tune <agent> ...`
- `maia agent purge <agent>`

### Messaging
- `maia send <from> <to> <message>`
- `maia inbox <agent>`
- `maia thread list`
- `maia thread show <thread>`
- `maia reply <agent> <thread> <message>`

### Artifacts / workspaces
- `maia artifact list [thread]`
- `maia artifact show <artifact>`
- `maia workspace show <agent>`

### Transfer
- `maia export [path]`
- `maia import <path>`
- `maia inspect <path>`

## UX / DX rules
- help text는 현재 구현 상태를 과장하지 않는다.
- runtime verb는 실제 runtime 의미와 맞아야 한다.
- import preview는 overwrite 가능한 모든 portable state를 보여줘야 한다.
- operator가 가장 자주 쓰는 흐름은 create → start → send → reply → artifact → status 여야 한다.

## Success criteria for foundation milestone
- running agent 두 개가 broker를 통해 thread 기반으로 여러 번 메시지를 왕복한다.
- question / answer / report kind가 동작한다.
- artifact reference를 thread에 연결할 수 있다.
- `maia agent start`가 실제 Docker runtime과 연결된다.
- 운영자가 thread와 agent status를 조회할 수 있다.
