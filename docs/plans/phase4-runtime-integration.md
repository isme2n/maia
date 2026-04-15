# Phase 4 Runtime Integration Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia의 agent lifecycle을 registry-only 상태 변경에서 실제 Docker runtime adapter 기반 동작으로 끌어올린다.

**Architecture:** Runtime contract는 유지하고, 실제 구현은 `DockerRuntimeAdapter`로 추가한다. 테스트는 실제 Docker daemon에 의존하지 않도록 fake docker CLI binary를 사용한다. CLI는 최소 surface만 확장해서 `agent tune`으로 runtime_spec을 설정하고 `agent start/stop/status/logs`를 runtime adapter에 연결한다.

**Tech Stack:** Python stdlib, subprocess-based Docker CLI invocation, JSON state storage, pytest.

---

## Phase 4 scope
- `RuntimeAdapter`의 실제 구현 추가
- runtime state persistence 추가
- `agent tune`에 runtime spec 설정 surface 추가
- `agent start` / `agent stop` / `agent status` runtime wiring
- `agent logs` 추가
- fake docker binary 기반 end-to-end 테스트 추가
- host Docker 미설치 상태에서도 doctor + fake runtime tests로 개발을 진행하고, 실제 host install은 별도 operator step으로 둔다

## Out of scope
- Docker Compose orchestration
- broker/RabbitMQ integration
- always-on daemon/watcher
- live agent message polling loop

## Task breakdown
1. Task 057 — phase4 doctor + host readiness bootstrap
2. Task 053 — runtime config CLI surface
3. Task 054 — runtime state storage + Docker adapter foundation
4. Task 055 — CLI wiring for start/stop/status/logs
5. Task 056 — hardening, review feedback, README/help alignment if needed

## Verification bar
- task별 targeted pytest
- `bash scripts/verify.sh`
- reviewer approve
- 기능 묶음 단위 commit
