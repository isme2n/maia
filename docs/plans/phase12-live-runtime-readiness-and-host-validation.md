# Phase 12 Live Runtime Readiness and Host Validation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia의 runtime 경로를 fake-docker 기반 신뢰도에서 한 단계 더 끌어올려, 실제 호스트에서도 operator가 무엇이 준비됐고 무엇이 아직 아닌지 분명하게 알 수 있게 만든다.

**Architecture:** Phase 12는 새 기능을 크게 늘리는 단계가 아니라, 이미 정리된 runtime operator path를 실제 호스트 검증과 지원 경계 측면에서 닫는 단계다. 핵심은 `maia doctor`, runtime 명령, README/help, smoke 검증을 “로컬 테스트에서는 어디까지 보장되는지”와 “실제 호스트에서는 무엇을 추가로 확인해야 하는지” 기준으로 정리하는 것이다.

**Tech Stack:** Python stdlib, existing Maia CLI/runtime modules, Docker CLI, pytest, current fake-docker test harness.

---

## Scope
- 실제 호스트 readiness 확인 흐름 강화
- doctor 결과와 live runtime validation 문서/출력 정렬
- fake-docker 검증과 real-host 검증의 경계 명시
- runtime 지원 범위와 알려진 한계 문서화
- 최종 host-validation checklist와 operator runbook 초안 정리

## Out of scope
- Docker Compose orchestration 확대
- broker/RabbitMQ 확장
- daemon/orchestrator 추가
- multi-host runtime coordination
- workspace sync/file transfer
- DB migration

## Phase principles
- 테스트 green과 실제 호스트 준비 상태를 절대 혼동하지 않는다.
- operator는 “지금 이 머신에서 실제로 실행 가능한지”를 한 번에 이해할 수 있어야 한다.
- 실패 메시지는 내부 구현 설명보다 다음 행동이 먼저 보여야 한다.
- fake-docker 검증은 유지하되, real-host 검증은 별도 체크리스트로 분리한다.
- 문서/도움말/검증 흐름이 같은 지원 범위를 말해야 한다.

## Runtime support boundary
- Fake-docker tests verify Maia's runtime command flow, not whether Docker works on this host.
- Run `maia doctor` on the host before using `agent start|stop|status|logs` for real.
- If `maia doctor` fails, fix Docker on the host first, then retry the runtime command.
- Broker-backed collaboration and runtime validation are separate checks.

## Recommended task breakdown
1. Task 087 — live-host runtime readiness contract locking
2. Task 088 — doctor output and host-validation guidance refinement
3. Task 089 — runtime support-boundary docs/help closeout
4. Task 090 — host-validation smoke checklist and runbook
5. Task 091 — phase12 final verify and release-closeout

## Task 087 — live-host runtime readiness contract locking

**Objective:** 실제 호스트에서 runtime 명령을 실행하기 전에 어떤 조건이 충족되어야 하는지 doctor/runtime contract를 명확히 잠근다.

**Files:**
- Modify: `src/maia/cli.py`
- Modify: `tests/test_cli_runtime.py`
- Reference: `src/maia/docker_runtime_adapter.py`
- Reference: `docs/plans/phase11-runtime-operator-path-hardening.md`

**What to lock:**
- Docker CLI 있음
- Docker daemon 접근 가능
- runtime spec configured
- workspace path configured
- operator가 “테스트는 통과했지만 이 머신에서는 Docker가 아직 안 됨” 상태를 구분할 수 있어야 함

**Validation:**
- `python3 -m pytest -q tests/test_cli_runtime.py -k "doctor or runtime"`

**Commit message:**
- `fix: lock live host runtime readiness contract`

## Task 088 — doctor output and host-validation guidance refinement

**Objective:** doctor의 detail/remediation/next_step이 실제 운영자가 그대로 따라갈 수 있는 수준으로 더 정리되게 한다.

**Files:**
- Modify: `src/maia/cli.py`
- Modify: `tests/test_cli_runtime.py`
- Modify: `tests/test_cli.py` (only if help/examples wording changes)

**What to improve:**
- Docker 미설치
- Docker 실행 안 됨
- 권한 문제로 Docker 접근 불가
- broker는 optional임을 더 분명히 유지
- “다음에 뭘 하면 되는지”를 짧고 분명하게 유지

**Validation:**
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py -k "doctor"`

**Commit message:**
- `docs: refine doctor guidance for live host validation`

## Task 089 — runtime support-boundary docs/help closeout

**Objective:** README/help에서 fake-docker 기반 보장 범위와 실제 호스트에서 추가로 필요한 검증 범위를 명확히 적는다.

**Files:**
- Modify: `README.md`
- Modify: `src/maia/cli_parser.py`
- Modify: `tests/test_cli.py`

**Docs/help points to align:**
- 무엇이 테스트로 보장되는지
- 실제 Docker host에서 operator가 추가로 확인해야 하는 것
- runtime commands는 Docker 준비 여부에 따라 달라진다는 점
- broker-backed collaboration과 runtime path를 헷갈리지 않게 분리

**Validation:**
- `python3 -m pytest -q tests/test_cli.py`

**Commit message:**
- `docs: clarify live runtime support boundary`

## Task 090 — host-validation smoke checklist and runbook

**Objective:** 실제 운영자가 host에서 Maia runtime을 확인할 때 따라갈 수 있는 짧은 점검 흐름을 만든다.

**Files:**
- Modify: `README.md`
- Create or Modify: `docs/plans/phase12-live-runtime-readiness-and-host-validation.md`
- Optional: `docs/` 내 별도 runbook 문서 추가
- Test: `tests/test_cli.py` (if checklist/help wording is surfaced)

**Minimum checklist:**
- `maia doctor`
- `maia agent new <name>`
- `maia agent tune <id> --runtime-image ... --runtime-workspace ... --runtime-command ... --runtime-env ...`
- `maia agent start <id>`
- `maia agent status <id>`
- `maia agent logs <id>`
- `maia agent stop <id>`

**Runbook guidance:**
- doctor fail일 때 먼저 볼 것
- start가 실패했을 때 확인할 것
- stale runtime이 감지됐을 때 할 일
- stop/logs/status가 기대와 다를 때 확인할 것

**Validation:**
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

**Commit message:**
- `docs: add host runtime validation runbook`

## Host validation runbook

### 1. 먼저 `maia doctor`
- Docker 관련 체크가 모두 `ok`인지 먼저 본다.
- 여기서 실패하면 runtime 명령보다 Docker 문제를 먼저 해결한다.

### 2. 에이전트를 만든 뒤 runtime 설정
- `maia agent new <name>`
- `maia agent tune <id> --runtime-image ... --runtime-workspace ... --runtime-command ... --runtime-env ...`
- 여기까지 끝나야 `start`를 시도할 준비가 된다.

### 3. `start`가 실패하면
- 다시 `maia doctor`
- 이미지 이름, workspace 경로, command, env 값을 다시 확인
- Docker가 꺼져 있거나 권한 문제가 없는지 확인

### 4. `status`가 기대와 다르면
- `stopped`면 실제 컨테이너가 이미 끝난 것일 수 있다.
- Maia가 오래된 saved runtime record를 지웠다면, 필요할 때 다시 `start`하면 된다.

### 5. `logs`가 안 나오면
- 먼저 `status`가 `running`인지 확인
- 이미 끝난 컨테이너면 `logs` 결과가 달라질 수 있으니 다시 `status`를 본다.
- stale runtime 경고가 나오면 Docker 상태를 확인한 뒤 다시 시작한다.

### 6. 마지막으로 `stop`
- `maia agent stop <id>`
- 이후 `maia agent status <id>`에서 `stopped`인지 확인

## Task 091 — phase12 final verify and release-closeout

**Objective:** Phase 12 범위를 verify/reviewer/docs alignment/clean worktree 기준으로 닫는다.

**Files:**
- Review: `README.md`
- Review: `src/maia/cli.py`
- Review: `src/maia/cli_parser.py`
- Review: `tests/test_cli.py`
- Review: `tests/test_cli_runtime.py`
- Review: `docs/plans/phase12-live-runtime-readiness-and-host-validation.md`

**Closeout checklist:**
- doctor guidance is clear and operator-friendly
- runtime support boundary is explicit
- fake-docker validation remains green
- host-validation checklist is documented
- `bash scripts/verify.sh` passes
- reviewer approve
- worktree clean at finish

**Validation:**
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py tests/test_runtime_adapter_contract.py`
- `bash scripts/verify.sh`

**Commit message:**
- `docs: close phase12 live runtime readiness`
- or `fix: close live runtime validation phase`

## Verification bar
- task별 targeted pytest
- runtime-related suite green
- docs/help/tests alignment maintained
- `bash scripts/verify.sh`
- reviewer approve
- clean worktree at finish

## Operator-facing completion criteria
- operator가 `maia doctor` 결과만 봐도 지금 이 머신에서 runtime을 시도해도 되는지 이해할 수 있다
- README/help가 fake-docker 검증과 real-host 검증의 차이를 숨기지 않는다
- runtime 관련 실패 메시지가 짧고 분명하며 다음 행동이 보인다
- host-validation checklist만 따라도 기본 runtime 경로를 점검할 수 있다
