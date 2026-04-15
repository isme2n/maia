# Phase 5 Host-Independent Hardening Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 호스트 Docker 접근 없이도 Maia의 운영 하드닝을 진행해서 runtime state hygiene, doctor UX, 안전한 상태 전이를 강화한다.

**Architecture:** Phase 5는 실제 infra install보다 앞서, control-plane 내부의 state integrity와 operator UX를 강화한다. runtime registry/runtime-state/doctor output의 일관성을 높이고, purge/import/status/logs 같은 운영 경로에서 stale state를 안전하게 다룬다.

**Tech Stack:** Python stdlib, existing Maia CLI/runtime modules, pytest.

---

## Scope
- runtime state cleanup / integrity hardening
- doctor remediation guidance
- stale runtime state safety checks
- import/purge/runtime state consistency

## Out of scope
- 실제 Docker/Compose 설치
- broker/live messaging transport 확장
- compose orchestration

## Task breakdown
1. Task 058 — runtime state hygiene on purge/import
2. Task 059 — doctor remediation UX hardening
3. Task 060 — runtime command safety and stale-state guardrails
4. Task 061 — phase5 host-independent final hardening

## Verification bar
- task별 targeted pytest
- `bash scripts/verify.sh`
- reviewer approve
- 기능 묶음 단위 commit
