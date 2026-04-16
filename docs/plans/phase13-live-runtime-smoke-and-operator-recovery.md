# Phase 13 Live Runtime Smoke and Operator Recovery Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia의 runtime 경로를 실제 운영자 관점에서 한 단계 더 닫아, live host에서 기본 smoke 흐름과 대표 recovery 흐름을 짧고 명확하게 검증할 수 있게 만든다.

**Architecture:** Phase 13은 새 기능을 넓히는 단계가 아니라, 이미 정리된 runtime/doctor/help/runbook을 실제 운영 점검 흐름으로 더 단단하게 묶는 단계다. 핵심은 live host 기준 smoke checklist, 대표 장애 복구 흐름, operator-facing 메시지, 그리고 문서/도움말/테스트의 일관성을 함께 잠그는 것이다. fake-docker 검증은 계속 유지하되, real-host smoke는 별도 checklist와 support boundary 안에서 다룬다.

**Tech Stack:** Python stdlib, existing Maia CLI/runtime modules, Docker CLI, pytest, fake-docker harness, current README/help/plan docs.

---

## Scope
- live host runtime smoke 흐름 정리
- 대표 operator recovery flow 정리
- doctor -> start/status/logs/stop 이어지는 실전 점검 흐름 강화
- README/help/runbook/operator examples 정렬
- 실제 호스트 검증 경계와 결과 보고 방식 고정

## Out of scope
- Docker Compose orchestration 확대
- broker/RabbitMQ 기능 확대
- daemon/orchestrator 추가
- multi-host runtime coordination
- workspace sync/file transfer
- DB migration

## Phase principles
- operator는 “지금 무엇을 먼저 확인해야 하는지”를 한 번에 이해할 수 있어야 한다.
- 실패 메시지는 짧고 분명해야 하며, 가능한 한 다음 행동을 보여야 한다.
- live host smoke와 fake-docker validation은 같은 것이 아님을 계속 분리해서 설명한다.
- recovery flow는 새 기능보다 실제 운영 복구 경험을 우선한다.
- 내부 구현 용어나 메타 설명은 operator-facing 문구에 섞지 않는다.

## Runtime support boundary
- Fake-docker tests verify Maia's runtime command flow, not whether Docker works on this host.
- Run `maia doctor` on the host before using `agent start|stop|status|logs` for real.
- If `maia doctor` fails, fix Docker on the host first, then retry the runtime command.
- Broker-backed collaboration and runtime validation are separate checks.

## Live host runtime recovery
- If doctor fails, fix Docker first.
- If start fails, rerun doctor and re-check the runtime image, workspace, command, and env values.
- If Maia says the saved runtime record is old, check Docker and start the agent again if needed.
- If status or logs show stopped, confirm whether the container already exited before restarting it.

## Recommended task breakdown
1. Task 092 — live host smoke contract locking
2. Task 093 — operator recovery flows hardening
3. Task 094 — runtime docs/help/examples closeout
4. Task 095 — host validation reporting contract
5. Task 096 — phase13 final verify and closeout

## Task 092 — live host smoke contract locking

**Objective:** 실제 호스트에서 운영자가 따라갈 기본 runtime smoke 흐름을 명확히 고정한다.

**Files:**
- Modify: `README.md`
- Modify: `src/maia/cli_parser.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_cli_runtime.py`
- Reference: `docs/plans/phase12-live-runtime-readiness-and-host-validation.md`

**Smoke flow to lock:**
- `maia doctor`
- `maia agent new <name>`
- `maia agent tune <id> --runtime-image ... --runtime-workspace ... --runtime-command ... --runtime-env ...`
- `maia agent start <id>`
- `maia agent status <id>`
- `maia agent logs <id>`
- `maia agent stop <id>`
- `maia agent status <id>` after stop

**Validation:**
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py -k "runtime or smoke or doctor"`

**Commit message:**
- `docs: lock live runtime smoke flow`

## Task 093 — operator recovery flows hardening

**Objective:** 실제 운영 중 자주 만나는 대표 recovery 흐름을 더 짧고 이해하기 쉽게 정리하고 테스트로 잠근다.

**Files:**
- Modify: `src/maia/cli.py`
- Modify: `tests/test_cli_runtime.py`
- Reference: `src/maia/docker_runtime_adapter.py`

**Recovery flows to cover:**
- Docker daemon 접근 실패
- permission denied for Docker daemon
- stale runtime state detected
- registry says running but live container already exited
- `logs` or `status` shows stopped when operator expected running
- restart가 필요할 때 operator가 다음 행동을 바로 알 수 있어야 함

**Validation:**
- `python3 -m pytest -q tests/test_cli_runtime.py -k "stale or permission or recovery or runtime"`

**Commit message:**
- `fix: harden runtime recovery guidance`

## Task 094 — runtime docs/help/examples closeout

**Objective:** README/help/examples가 실제 운영자 기준으로 같은 흐름을 말하도록 더 다듬는다.

**Files:**
- Modify: `README.md`
- Modify: `src/maia/cli_parser.py`
- Modify: `tests/test_cli.py`

**What to align:**
- Quickstart는 여전히 local portable-state 경로임을 유지
- live host runtime smoke는 별도 checklist로 분리
- runtime support boundary와 recovery guidance가 충돌하지 않게 정리
- 예시는 가능한 한 짧고 실제 operator가 바로 복사해서 이해 가능한 수준 유지

**Validation:**
- `python3 -m pytest -q tests/test_cli.py`

**Commit message:**
- `docs: align live runtime examples and recovery help`

## Task 095 — host validation reporting contract

**Objective:** 실제 호스트에서 smoke를 수행한 뒤 결과를 어떻게 보고할지 포맷과 기준을 정리한다.

**Files:**
- Modify: `docs/plans/phase13-live-runtime-smoke-and-operator-recovery.md`
- Modify: `README.md` (if needed)
- Optional: 별도 runbook/status note 문서 추가

**Reporting contract:**
- code/tests green 여부
- doctor 결과
- live host smoke 성공/실패 여부
- 실패 시 어느 단계에서 막혔는지
- 다음 operator action 한 줄 요약

**Validation:**
- docs alignment check via `python3 -m pytest -q tests/test_cli.py`

**Commit message:**
- `docs: define live host validation reporting contract`

## Live host validation report template
- `doctor=ok|fail`
- `live_runtime_smoke=ok|fail`
- `failed_step=-|doctor|start|status|logs|stop`
- `next_action=<one short sentence>`

### Example success report
- `doctor=ok`
- `live_runtime_smoke=ok`
- `failed_step=-`
- `next_action=No action needed`

### Example blocked report
- `doctor=fail`
- `live_runtime_smoke=fail`
- `failed_step=doctor`
- `next_action=Fix Docker on the host, then rerun maia doctor`

## Task 096 — phase13 final verify and closeout

**Objective:** Phase 13 범위를 verify/reviewer/docs alignment/clean worktree 기준으로 닫는다.

**Files:**
- Review: `README.md`
- Review: `src/maia/cli.py`
- Review: `src/maia/cli_parser.py`
- Review: `tests/test_cli.py`
- Review: `tests/test_cli_runtime.py`
- Review: `docs/plans/phase13-live-runtime-smoke-and-operator-recovery.md`

**Closeout checklist:**
- live host smoke flow is explicit
- operator recovery guidance is clear
- docs/help/examples align
- fake-docker validation remains green
- `bash scripts/verify.sh` passes
- reviewer approve
- clean worktree at finish

**Validation:**
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py tests/test_runtime_adapter_contract.py`
- `bash scripts/verify.sh`

**Commit message:**
- `docs: close phase13 live runtime smoke`
- or `fix: close runtime smoke and recovery phase`

## Verification bar
- task별 targeted pytest
- runtime-related suite green
- docs/help/tests alignment maintained
- `bash scripts/verify.sh`
- reviewer approve
- clean worktree at finish

## Operator-facing completion criteria
- operator가 실제 host에서 smoke를 어떤 순서로 해야 하는지 바로 이해할 수 있다
- 문제가 생겼을 때 recovery flow가 짧고 분명하다
- README/help/runbook이 같은 지원 범위를 말한다
- live host 결과를 팀에 보고할 때 형식이 일관된다
