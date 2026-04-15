# Phase 9 Golden-Flow Integration Closing Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia의 v1 대표 operator flow를 실제 통합 시나리오 기준으로 고정해서, create/tune/start/send/reply/handoff/thread/workspace/status/logs 흐름이 한 덩어리로 안정적으로 재현되게 만든다.

**Architecture:** Phase 8까지 Maia는 control-plane surface를 대부분 갖췄다. Phase 9는 새 큰 축을 추가하지 않고, 기존 public commands를 “제품 대표 시나리오” 기준으로 통합해서 잠그는 단계다. 핵심은 broker/runtime/workspace/handoff/thread/status가 따로 존재하는 상태에서 끝내지 않고, operator가 실제 팀을 운영하는 흐름으로 연결해서 smoke/integration 기준을 고정하는 것이다.

**Tech Stack:** Python stdlib, existing Maia CLI/parser/runtime/broker/collaboration modules, pytest.

---

## Scope
- v1 golden operator flows를 명시적으로 고정
- end-to-end CLI integration coverage 강화
- command/output contract를 대표 흐름 기준으로 정리
- handoff/thread/workspace/status/logs 흐름 연결 보강

## Out of scope
- always-on daemon
- PostgreSQL migration
- file sync engine
- full agent SDK
- broker retry/dead-letter expansion

## Ground rules
- control plane + transport split은 유지한다.
- public terminology는 handoff 기준으로 유지한다.
- 새 infra 축을 열지 말고 existing surface를 통합/고정한다.
- 대표 흐름은 문서와 테스트가 같은 순서를 보여야 한다.

## Recommended task breakdown
1. Task 074 — v1 golden-flow smoke contract and operator examples
2. Task 075 — integrated collaboration lifecycle regression suite
3. Task 076 — handoff/workspace/status/logs operator-link hardening
4. Task 077 — final golden-flow UX alignment and cleanup

## Verification bar
- task별 targeted pytest
- representative smoke command sequence green
- `bash scripts/verify.sh`
- reviewer approve
- 기능 묶음 단위 selective commit
