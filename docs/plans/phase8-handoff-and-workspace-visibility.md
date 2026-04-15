# Phase 8 Handoff and Workspace Visibility Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia의 collaboration plane에서 잘못 다시 떠오른 artifact 용어를 handoff로 바로잡고, operator가 agent workspace와 handoff location을 함께 볼 수 있게 해서 handoff/workspace plane을 control-plane 기준으로 완성한다.

**Architecture:** Phase 7까지 Maia는 thread/message/handoff visibility의 기반을 갖췄다. Phase 8은 broker나 runtime을 더 무겁게 만들지 않고, public terminology를 handoff로 통일하고, workspace는 실제 파일 동기화 시스템이 아니라 operator-visible location/context surface로 붙인다. 즉 `누가 누구에게 무엇을 어디로 넘겼는가`를 thread + handoff + workspace 기준으로 보이게 만드는 phase다.

**Tech Stack:** Python stdlib, existing Maia CLI/parser/storage/runtime modules, HandoffRecord, RuntimeSpec, pytest.

---

## Scope
- public CLI/docs/output에서 artifact terminology를 handoff로 정리
- `handoff add/list/show` CLI surface 도입
- `workspace show <agent>` CLI surface 추가
- thread visibility에서 handoff/workspace context 보강
- README/help를 handoff-first operator workflow로 정리

## Out of scope
- file copy engine
- shared workspace sync daemon
- in-container SDK loop
- broker retry/dead-letter expansion
- portable export/import scope expansion

## Ground rules
- public surface는 handoff terminology를 사용한다.
- Handoff는 실제 payload 저장소가 아니라 pointer/location metadata다.
- workspace visibility는 operator context 제공이 목적이지 파일 브라우저 전체 구현이 아니다.
- broker는 계속 transport detail로만 남긴다.
- runtime visibility는 existing runtime state/runtime spec만 재사용한다.

## Task breakdown
1. Task 070 — rename public artifact surface to handoff
2. Task 071 — workspace show CLI foundation
3. Task 072 — thread detail handoff/workspace context
4. Task 073 — README/help/operator flow hardening for handoff-first UX

## Verification bar
- task별 targeted pytest
- `bash scripts/verify.sh`
- reviewer approve
- 기능 묶음 단위 selective commit
