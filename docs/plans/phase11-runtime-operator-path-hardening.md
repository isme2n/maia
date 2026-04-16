# Phase 11 Runtime Operator Path Hardening Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia의 runtime 경로를 문서/계약 수준에서 한 단계 더 밀어, 실제 operator가 `agent start|stop|status|logs`를 신뢰할 수 있는 control-plane 경로로 강화한다.

**Architecture:** Phase 11은 새 product plane을 넓히는 단계가 아니라, 이미 존재하는 Docker-backed runtime surface를 더 실제 운영 경로답게 다듬는 단계다. 핵심은 `doctor`, `DockerRuntimeAdapter`, CLI error policy, persisted runtime state, fake-docker 기반 검증을 하나의 일관된 operator contract로 잠그는 것이다. 실제 host Docker 설치 여부와 무관하게 진행 가능한 host-independent hardening을 우선하고, live-host 검증은 별도 operator step으로 분리한다.

**Tech Stack:** Python stdlib, existing Maia CLI/runtime modules, subprocess-based Docker CLI invocation, JSON runtime state storage, pytest.

---

## Scope
- runtime state vs live Docker state mismatch 정책 고정
- `agent start|stop|status|logs` failure matrix hardening
- `maia doctor`와 runtime command 에러 wording 정렬
- fake-docker 기반 runtime golden flow 강화
- runtime support boundary 문서/헬프 정렬

## Out of scope
- Docker Compose orchestration 확대
- broker/RabbitMQ 기능 확장
- daemon/orchestrator 추가
- workspace sync/file transfer
- DB migration
- multi-host runtime coordination

## Phase principles
- 실제 host readiness와 code/test completion을 분리해서 보고한다.
- operator가 실패 원인을 바로 이해할 수 있어야 한다.
- persisted runtime state는 독립적인 integrity surface로 취급한다.
- live Docker path가 없더라도 fake-docker로 대부분의 control-plane 계약을 고정한다.
- 새 기능 추가보다 기존 runtime path의 신뢰도를 올린다.

## Recommended task breakdown
1. Task 082 — runtime mismatch contract definition
2. Task 083 — start/stop/status/logs failure matrix hardening
3. Task 084 — doctor/runtime error wording alignment
4. Task 085 — runtime golden-flow smoke strengthening
5. Task 086 — phase11 final hardening and docs boundary closeout

## Task 082 — runtime mismatch contract definition

**Objective:** persisted runtime state와 live Docker state가 어긋날 때 Maia가 어떤 상태를 stale/missing/active로 볼지 명확히 정의하고 테스트로 고정한다.

**Files:**
- Modify: `src/maia/docker_runtime_adapter.py`
- Modify: `src/maia/cli.py`
- Test: `tests/test_docker_runtime_adapter.py`
- Test: `tests/test_cli_runtime.py`
- Reference: `src/maia/runtime_adapter.py`
- Reference: `src/maia/runtime_state_storage.py`

**Required behaviors to lock:**
- local runtime state exists + live container missing -> stale runtime state로 취급하고 operator-facing 에러를 반환
- local runtime state exists + live status resolves to exited/dead -> stopped로 동기화할지, stale로 취급할지 정책을 하나로 통일
- local runtime state missing + runtime spec exists -> `status`/`logs`/`stop`가 “configured but not active” 류의 명확한 에러를 반환
- local runtime state exists + runtime spec cleared later -> state-first inspection path를 유지하되 wording은 명확히 한다

**Validation:**
- `python3 -m pytest -q tests/test_docker_runtime_adapter.py tests/test_cli_runtime.py -k "stale or mismatch or missing"`

**Commit message:**
- `test: lock runtime mismatch policy`
- or `fix: harden runtime mismatch handling`

## Task 083 — start/stop/status/logs failure matrix hardening

**Objective:** 주요 runtime 명령의 성공/실패 전이 규칙을 더 세밀하게 정의하고, double-start / missing-active-runtime / handle mismatch 같은 경계를 테스트로 잠근다.

**Files:**
- Modify: `src/maia/cli.py`
- Modify: `src/maia/docker_runtime_adapter.py`
- Test: `tests/test_cli_runtime.py`
- Test: `tests/test_runtime_adapter_contract.py`

**Failure matrix to cover:**
- `start` when already active runtime exists
- `start` when runtime spec missing
- `stop` when no active runtime state exists
- `stop` when saved runtime handle no longer exists in Docker
- `status` when runtime state exists but inspect fails
- `logs` when runtime state exists but logs command fails
- `logs` when stderr contains meaningful output
- command-specific errors should mention the operator action and the agent/runtime handle context where possible

**Validation:**
- `python3 -m pytest -q tests/test_cli_runtime.py tests/test_runtime_adapter_contract.py`

**Commit message:**
- `fix: harden runtime command failure matrix`

## Task 084 — doctor/runtime error wording alignment

**Objective:** `maia doctor`가 제시하는 remediation과 실제 runtime command 실패 메시지가 같은 operator mental model을 공유하도록 wording을 정렬한다.

**Files:**
- Modify: `src/maia/cli.py`
- Modify: `src/maia/cli_parser.py` (only if help text/examples need adjustment)
- Test: `tests/test_cli.py`
- Test: `tests/test_cli_runtime.py`
- Reference: `docs/plans/phase10-release-hardening-and-v1-closeout.md`

**What to align:**
- docker CLI missing
- docker compose missing
- docker daemon unreachable
- runtime spec missing
- workspace missing
- stale runtime state detected
- next-step/remediation wording should point operator to the right next action instead of only restating failure

**Validation:**
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py -k "doctor or runtime"`

**Commit message:**
- `docs: align runtime and doctor error wording`
- or `fix: align doctor and runtime remediation`

## Task 085 — runtime golden-flow smoke strengthening

**Objective:** fake-docker 기반 대표 operator flow를 runtime 중심으로 보강해서 create/tune/start/status/logs/stop의 end-to-end contract를 더 강하게 잠근다.

**Files:**
- Modify: `tests/test_cli_runtime.py`
- Modify: `README.md` (only if support boundary/examples need wording updates)
- Modify: `src/maia/cli_parser.py` (only if help text changes)

**Minimum runtime smoke flow:**
- `maia doctor`
- `maia agent new planner`
- `maia agent tune <agent_id> --runtime-image ... --runtime-workspace ... --runtime-command ...`
- `maia agent start <agent_id>`
- `maia agent status <agent_id>`
- `maia agent logs <agent_id> --tail-lines 20`
- `maia agent stop <agent_id>`
- `maia agent status <agent_id>` after stop

**Strengthening goals:**
- fake docker state transitions should mimic enough real CLI behavior to exercise stale/active/exited distinctions
- smoke should prove the runtime path independently of collaboration/broker concerns
- if a support-boundary note is added, keep README/help/tests aligned

**Validation:**
- `python3 -m pytest -q tests/test_cli_runtime.py -k "golden_flow or runtime"`

**Commit message:**
- `test: strengthen runtime golden flow smoke`

## Task 086 — phase11 final hardening and docs boundary closeout

**Objective:** Phase 11 범위를 final verify, reviewer loop, docs/help consistency, clean worktree 기준으로 닫는다.

**Files:**
- Review: `README.md`
- Review: `src/maia/cli.py`
- Review: `src/maia/cli_parser.py`
- Review: `tests/test_cli.py`
- Review: `tests/test_cli_runtime.py`
- Review: `tests/test_docker_runtime_adapter.py`
- Review: `tests/test_runtime_adapter_contract.py`

**Closeout checklist:**
- runtime mismatch policy is explicit and tested
- doctor/runtime wording is aligned
- runtime golden flow passes in fake-docker environment
- `bash scripts/verify.sh` passes
- reviewer approve
- worktree clean at finish

**Validation:**
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py tests/test_runtime_adapter_contract.py`
- `bash scripts/verify.sh`

**Commit message:**
- `docs: close phase11 runtime operator hardening`
- or `fix: close runtime operator path hardening`

## Verification bar
- task별 targeted pytest
- runtime-related suite stays green:
  - `tests/test_cli_runtime.py`
  - `tests/test_docker_runtime_adapter.py`
  - `tests/test_runtime_adapter_contract.py`
- `bash scripts/verify.sh`
- reviewer approve
- 기능 묶음 단위 commit
- worktree clean at finish

## Operator-facing completion criteria
- `maia doctor` and runtime commands fail clearly and consistently
- operator can distinguish config missing vs active runtime missing vs stale runtime state
- runtime smoke path is reproducible with fake docker
- host Docker live validation remains an explicit separate operator step, not an implied guarantee
