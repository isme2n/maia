# Phase 7 Collaboration Visibility and Artifact Handoffs Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia의 broker-backed collaboration을 operator-visible control plane으로 완성해서, thread 상태를 한눈에 보고 thread에 연결된 artifact/handoff를 안전하게 기록·조회할 수 있게 만든다.

**Architecture:** Phase 6에서 live broker transport는 이미 붙었으므로, Phase 7은 transport를 더 복잡하게 만들지 않고 control-plane visibility를 완성한다. public surface는 계속 agent/thread/message/artifact 중심을 유지하고, artifact는 실제 payload 저장소가 아니라 thread-linked pointer metadata로만 다룬다. runtime visibility는 기존 Docker runtime state를 재사용해서 thread 참여자 상태를 보여주되, 새로운 daemon이나 heartbeat 체계는 도입하지 않는다.

**Tech Stack:** Python stdlib, existing Maia CLI/parser/storage/runtime modules, existing HandoffRecord model, pytest.

---

## Scope
- collaboration storage에 handoff/artifact metadata 추가
- public artifact CLI (`artifact add/list/show`) 추가
- operator thread overview (`thread list`) 추가
- thread detail에 artifact count / pending_on / participant runtime status 추가
- help/README를 실제 collaboration workflow 기준으로 정리

## Out of scope
- blob/file copy engine
- shared workspace sync
- broker retry/dead-letter sophistication
- always-on daemon or agent SDK loop
- portable export/import scope 확장

## Ground rules
- broker는 계속 transport detail로만 남긴다.
- public UX는 queue 용어가 아니라 agent/thread/artifact 용어를 유지한다.
- artifact는 thread-linked pointer metadata만 저장한다.
- thread waiting state는 가능하면 latest message에서 derive한다.
- runtime visibility는 existing runtime state를 재사용한다.

## Task breakdown
1. Task 066 — collaboration storage v2 with handoff persistence
2. Task 067 — artifact CLI surface and validation
3. Task 068 — thread list/show operator visibility
4. Task 069 — runtime-enriched thread visibility and phase7 UX polish

## Verification bar
- task별 targeted pytest
- `bash scripts/verify.sh`
- reviewer approve
- 기능 묶음 단위 selective commit
