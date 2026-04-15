# Phase 10 Release Hardening and v1 Closeout Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia를 v1 release candidate 수준으로 닫기 위해, 실패 모드/운영 문서/지원 범위/최종 검증 기준을 고정하고 “지금 되는 것과 아직 아닌 것”을 명확히 한다.

**Architecture:** Phase 10은 기능 확장보다 제품 경계와 운영 안정성을 마감하는 단계다. Control plane로서 Maia가 무엇을 책임지고 무엇을 책임지지 않는지, operator가 실패 시 무엇을 확인해야 하는지, quickstart와 known limitations가 무엇인지 문서와 출력 계약으로 잠근다. 이 단계가 끝나면 Maia는 “기능 데모”가 아니라 “마감 가능한 v1” 상태여야 한다.

**Tech Stack:** Python stdlib, existing Maia CLI/docs/test harness, pytest.

---

## Scope
- failure-mode hardening and error-surface alignment
- quickstart / known limitations / support-boundary docs 고정
- release checklist / smoke checklist 고정
- final verification and clean-worktree release closeout

## Out of scope
- new product planes
- daemon/orchestrator
- DB migration
- sync/file transfer subsystem
- advanced broker/runtime features

## Ground rules
- README/help는 실제 구현을 과장하지 않는다.
- unsupported scope는 문서에 명시한다.
- operator가 실패 원인을 바로 이해할 수 있어야 한다.
- release closeout 기준은 테스트 green + smoke green + docs alignment다.

## Recommended task breakdown
1. Task 078 — failure-mode and error-message hardening
2. Task 079 — quickstart and known-limitations closeout docs
3. Task 080 — v1 release checklist and smoke checklist locking
4. Task 081 — final release-candidate verify and cleanup

## Verification bar
- targeted failure-mode tests green
- `bash scripts/verify.sh`
- clean install/quickstart smoke green
- reviewer approve
- worktree clean at finish
