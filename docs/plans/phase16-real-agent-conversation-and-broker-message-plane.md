# Phase 16 Real Agent Conversation and Broker Message Plane Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia Part 2를 실제 running agent들이 broker/message plane 위에서 여러 번 왕복 대화하는 제품 단계로 닫는다.

**Architecture:** Maia는 계속 control plane으로 남고, 실제 대화는 running Hermes agents와 broker가 담당한다. SQLite collaboration state는 thread/message/handoff visibility와 local cache/history source로 유지하되, live delivery source-of-truth는 broker inbox/outbox semantics로 정리한다.

**Tech Stack:** Python stdlib, existing Maia CLI/runtime modules, SQLite state, RabbitMQ broker adapter, Docker runtime, pytest.

---

## Product contract to lock

### Part 2 public story
1. operator가 shared infra와 agent runtime을 준비한다.
2. running agent A가 broker를 통해 running agent B에게 request/question/report/handoff를 보낸다.
3. running agent B는 broker inbox에서 delivery를 받고 응답한다.
4. Maia는 thread/message/handoff/workspace visibility를 보여준다.
5. operator는 누가 pending인지, 어느 thread가 열려 있는지, 최근 handoff가 무엇인지 볼 수 있다.
6. running agents talk to each other over the broker/message plane.

### What Part 2 is not
- 사람이 CLI로 직접 모든 메시지를 relay하는 제품
- one-shot task queue만 있는 제품
- control plane이 live transport hub 자체가 되는 구조

### Hard rules
- Maia는 control plane이다.
- live delivery는 broker가 담당한다.
- agent-to-agent interaction은 thread/message/handoff 중심으로 보인다.
- `send` / `reply` / `inbox`는 존재하더라도 operator debug/diagnostic 성격이지 제품 정체성이 아니다.
- local collaboration state는 cache/history/visibility 용도이며, real broker inbox semantics를 흐리지 않는다.

---

## Scope
- broker-backed live delivery path hardening
- real ack semantics and empty-inbox semantics 정리
- pulled broker messages를 local collaboration cache/history와 thread visibility에 merge
- thread/message/handoff/workspace visibility를 running agent collaboration 기준으로 정렬
- Part 2 README/help/tests/operator examples 정렬

## Out of scope
- 새로운 broker 종류 추가
- daemonized autonomous supervisor 추가
- web UI
- export/import final closeout
- open-source repo polish

---

## Recommended task breakdown
1. Task 109 — Part 2 contract and public surface lock
2. Task 110 — broker delivery semantics and inbox ack policy hardening
3. Task 111 — broker pull merge into local collaboration cache/thread state
4. Task 112 — running-agent multi-turn conversation regression flow
5. Task 113 — operator visibility for pending threads and recent handoffs
6. Task 114 — Part 2 docs/help/tests closeout

---

## Task 109 — Part 2 contract and public surface lock

**Objective:** README/PRD/help/tests에 Part 2를 “real agent conversation”으로 먼저 잠근다.

**Files:**
- Modify: `README.md`
- Modify: `docs/prd/maia-core-product.md`
- Modify: `src/maia/cli_parser.py`
- Modify: `tests/test_cli.py`
- Modify: `docs/plans/maia-product-roadmap-5-parts.md`
- Modify: `docs/plans/phase16-real-agent-conversation-and-broker-message-plane.md`

**Required changes:**
- Part 2 설명을 `running agents talk over broker` 기준으로 적는다.
- README/help에서 `send` / `reply` / `inbox`가 제품 정체성처럼 보이지 않게 낮춘다.
- `thread` / `handoff` / `workspace`는 visibility surface로 위치시킨다.
- Part 2 success criteria와 non-goals를 문서에 고정한다.

**Validation:**
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

**Commit message:**
- `docs: lock part2 real agent conversation contract`

---

## Task 110 — broker delivery semantics and inbox ack policy hardening

**Objective:** broker를 live delivery source-of-truth로 다듬고 ack/empty policy를 명확히 한다.

**Files:**
- Modify: `src/maia/cli.py`
- Modify: `src/maia/rabbitmq_broker.py`
- Modify: `src/maia/broker.py` (정말 필요한 최소 helper만)
- Test: `tests/test_cli.py`
- Test: `tests/test_cli_runtime.py`
- Test: `tests/test_rabbitmq_broker.py`

**Required changes:**
- broker inbox 출력에 source/ack policy가 분명히 드러나게 한다.
- real ack flow가 있는 상태에서는 empty broker pull을 진짜 empty live inbox로 취급한다.
- ack failure는 operator-facing error로 surface한다.
- publish ordering은 partial-success를 만들지 않도록 broker-first 원칙을 유지한다.

**Validation:**
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_rabbitmq_broker.py tests/test_cli.py tests/test_cli_runtime.py`

**Commit message:**
- `feat: harden broker inbox ack semantics`

---

## Task 111 — broker pull merge into local collaboration cache/thread state

**Objective:** broker delivery와 local thread/reply/history continuity를 일관되게 만든다.

**Files:**
- Modify: `src/maia/cli.py`
- Modify: `src/maia/collaboration_storage.py`
- Modify: `src/maia/message_model.py` (필요 시 최소 보강)
- Test: `tests/test_cli.py`
- Test: `tests/test_cli_runtime.py`
- Test: `tests/test_rabbitmq_broker.py`

**Required changes:**
- broker pull 결과를 dedupe하면서 local collaboration state에 merge한다.
- missing thread를 synthetic placeholder로 만들 때 topic/participants/updated_at을 올바르게 보존한다.
- broker-delivered message에 대한 `reply <message_id>`와 `thread show <thread_id>` continuity를 고정한다.
- thread topic metadata round-trip이 필요하면 RabbitMQ metadata path를 계속 사용한다.

**Validation:**
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_rabbitmq_broker.py`

**Commit message:**
- `feat: merge broker deliveries into collaboration cache`

---

## Task 112 — running-agent multi-turn conversation regression flow

**Objective:** running agents 기준으로 request → answer → report/handoff의 multi-turn flow를 regression으로 잠근다.

**Files:**
- Modify: `tests/test_cli_runtime.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md` (필요 시 최소 operator example only)

**Required changes:**
- 최소 2개 running agent가 등장하는 golden conversation regression 추가.
- 흐름 예시:
  - planner starts
  - reviewer starts
  - planner -> reviewer request
  - reviewer inbox pull + ack
  - reviewer -> planner answer/report
  - thread visibility reflects both turns
- stale/malformed collaboration/runtime 상태에서 어디서 깨지는지 operator-visible하게 고정한다.

**Validation:**
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py tests/test_cli.py`

**Commit message:**
- `test: lock running-agent conversation flow`

---

## Task 113 — operator visibility for pending threads and recent handoffs

**Objective:** operator가 현재 conversation plane 상태를 요약해서 볼 수 있게 visibility surface를 정리한다.

**Files:**
- Modify: `src/maia/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_cli_runtime.py`
- Modify: `README.md`

**Required changes:**
- `thread list/show`가 pending_on, recent handoff, participant runtime 상태를 더 명확하게 보여준다.
- operator가 “누가 대기 중인지 / 최근 handoff가 무엇인지 / 어느 runtime이 연결돼 있는지”를 볼 수 있어야 한다.
- workspace/handoff/thread/status/logs가 하나의 visibility story로 이어지게 한다.

**Validation:**
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

**Commit message:**
- `feat: improve conversation visibility surfaces`

---

## Task 114 — Part 2 docs/help/tests closeout

**Objective:** Part 2 public story를 README/help/tests에서 동일하게 닫는다.

**Files:**
- Modify: `README.md`
- Modify: `docs/prd/maia-core-product.md`
- Modify: `src/maia/cli_parser.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_cli_runtime.py`
- Modify: `docs/plans/phase16-real-agent-conversation-and-broker-message-plane.md`
- Modify: `docs/plans/maia-product-roadmap-5-parts.md`

**Required changes:**
- README/examples/help가 Part 2를 “real broker-backed agent conversation + visibility”로 설명한다.
- CLI messenger처럼 보이는 문구를 제거하거나 debug surface로 낮춘다.
- Part 2 completion criteria를 roadmap tracker에 반영할 준비를 한다.

**Validation:**
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `cd /home/asle/maia && bash scripts/verify.sh`

**Commit message:**
- `docs: close part2 real agent conversation flow`

---

## Verification bar
- task별 targeted pytest
- full verify where relevant
- docs/help/tests alignment
- reviewer approve
- clean worktree

## Acceptance criteria
- running agent 두 개 이상이 broker를 통해 multi-turn message exchange를 한다.
- Maia는 thread/message/handoff/workspace visibility를 operator에게 보여준다.
- 제품이 사람이 수동으로 중계하는 CLI messenger처럼 보이지 않는다.
- broker delivery semantics와 local cache/history semantics가 명확히 분리된다.
