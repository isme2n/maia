# Phase 15 Minimal Agent Bootstrap and Runtime Setup Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Maia를 `doctor → setup → agent new → agent setup → agent start`의 단순한 운영 흐름으로 재정렬해서, 일반 사용자가 여러 Hermes 에이전트를 만들고 실행할 수 있게 한다.

**Architecture:** Maia는 Hermes를 재구현하지 않는 control plane으로 남는다. Maia는 Docker/RabbitMQ/SQLite 기반의 공용 인프라와 에이전트 lifecycle만 관리하고, `agent setup`에서는 해당 에이전트 환경 안에서 `hermes setup`을 그대로 실행해 PTY를 중계한다. Hermes 설정 로직, 로그인 절차, provider/API key UX는 Maia가 소유하지 않는다.

**Tech Stack:** Python stdlib, existing Maia CLI/runtime modules, Docker CLI, RabbitMQ container, SQLite, pytest.

---

## Product contract to lock

### Public command flow
1. `maia doctor`
2. `maia setup`
3. `maia agent new <name>`
4. `maia agent setup <name>`
5. `maia agent start <name>`
6. `maia agent stop|status|logs <name>`

### Command responsibilities
- `doctor`
  - Docker usable?
  - Queue usable?
  - DB usable?
  - Only infra readiness; no Hermes login/API key/provider checks.
- `setup`
  - Bring up shared infra only.
  - RabbitMQ container/network/volumes.
  - Initialize Maia SQLite state DB.
  - No team defaults, no model policy wizard.
- `agent new`
  - Register agent identity only.
  - Public story: create the agent record by name.
  - No provider/model/runtime-image/login questions.
- `agent setup`
  - Launch or attach to the agent’s setup container/session.
  - Execute `hermes setup` exactly as Hermes provides it.
  - PTY passthrough only; Maia does not reinterpret setup screens.
  - Persist resulting Hermes home/config in that agent’s dedicated volume.
- `agent start`
  - Start only after successful `agent setup`.
  - Use the saved per-agent Hermes home/config volume.
  - Connect to the shared queue.

## Scope
- Minimal public CLI contract 재정렬
- RabbitMQ + SQLite 기반 shared infra bootstrap
- JSON registry에서 SQLite-backed control-plane state로 수렴
- Agent identity surface 단순화
- `agent setup` PTY passthrough 설계/구현
- `agent start` setup-gated runtime launch
- README/help/tests를 새 흐름으로 정렬

## Out of scope
- Maia가 Hermes setup wizard를 재구현하는 것
- model/team default/override 계층 설계
- gateway setup 자동화
- broker abstraction 확대
- PostgreSQL 도입
- web UI
- autonomous agent conversation logic 자체 구현

## Ground rules
- Maia는 Hermes setup 내용을 해석하지 않는다.
- Maia는 infra/control plane만 소유한다.
- 에이전트 1개 = Hermes 컨테이너 1개.
- Shared infra는 RabbitMQ + SQLite다.
- 일반 사용자 경로는 짧아야 한다.
- `send/reply` 중심 서사가 아니라 lifecycle/setup 중심 서사로 바꾼다.

## Recommended task breakdown
1. Task 102 — minimal product contract and CLI surface lock
2. Task 103 — SQLite control-plane state foundation
3. Task 104 — shared infra doctor/setup bootstrap
4. Task 105 — minimal agent identity creation flow
5. Task 106 — `agent setup` PTY passthrough for `hermes setup`
6. Task 107 — setup-gated `agent start|stop|status|logs`
7. Task 108 — docs/help/tests closeout and scope cleanup

---

## Task 102 — minimal product contract and CLI surface lock

**Objective:** 새 제품 흐름을 README/help/tests/plan 문서에서 먼저 고정한다.

**Files:**
- Modify: `README.md`
- Modify: `src/maia/cli_parser.py`
- Modify: `docs/prd/maia-core-product.md`
- Modify: `tests/test_cli.py`
- Modify: `docs/plans/phase15-minimal-agent-bootstrap-and-runtime-setup.md`

**Required changes:**
- README top section을 `doctor/setup/agent new/agent setup/agent start` 중심으로 교체.
- `doctor` 설명에서 Hermes auth/provider/login 체크 문구 제거.
- `setup` 설명에서 team defaults/model defaults 제거.
- `agent new` examples를 identity-only 흐름으로 단순화.
- `agent setup` command를 public help에 추가.
- `send/reply/inbox/thread`는 public 핵심 흐름 예시에서 제거하거나 debug/internal 성격으로 명확히 낮춘다.

**Validation:**
- `PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

**Commit message:**
- `docs: lock minimal maia bootstrap contract`

---

## Task 103 — SQLite control-plane state foundation

**Objective:** JSON 파일 조합을 줄이고 Maia control-plane source-of-truth를 SQLite로 옮긴다.

**Files:**
- Create: `src/maia/sqlite_state.py`
- Modify: `src/maia/app_state.py`
- Modify: `src/maia/storage.py`
- Modify: `src/maia/runtime_state_storage.py`
- Modify: `src/maia/collaboration_storage.py`
- Modify: `src/maia/cli.py`
- Test: `tests/test_sqlite_state.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_cli_runtime.py`

**Required changes:**
- Add SQLite DB path under `~/.maia/state.db`.
- Persist at minimum:
  - agents
  - runtime presence/setup status
  - infra bootstrap status
  - collaboration metadata if still needed
- Keep portable export/import contract explicit; SQLite is local runtime/control-plane store, not portable bundle format.
- Do not introduce PostgreSQL.
- If keeping some JSON temporarily, label them as transitional/local caches only.

**Validation:**
- `PYTHONPATH=src python3 -m pytest -q tests/test_sqlite_state.py tests/test_cli.py tests/test_cli_runtime.py`

**Commit message:**
- `feat: add sqlite control plane state`

---

## Task 104 — shared infra doctor/setup bootstrap

**Objective:** `doctor` and `setup`를 Maia shared infra 전용 흐름으로 만든다.

**Files:**
- Modify: `src/maia/cli.py`
- Modify: `src/maia/cli_parser.py`
- Modify: `src/maia/app_state.py`
- Create: `src/maia/infra_runtime.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_cli_runtime.py`
- Modify: `README.md`

**Required changes:**
- `doctor` checks only:
  - Docker CLI
  - Docker daemon
  - RabbitMQ infra container or reachability
  - SQLite DB path writable/usable
- `doctor` must not inspect Hermes credentials, provider auth, or login state.
- Add `setup` top-level command.
- `setup` should:
  - create Maia network/volumes if needed
  - start RabbitMQ container if absent
  - initialize SQLite schema
  - write infra-ready markers/state
- `setup` output must be plain operator language.

**Validation:**
- `PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

**Commit message:**
- `feat: add maia infra doctor and setup`

---

## Task 105 — minimal agent identity creation flow

**Objective:** `agent new`를 identity registration command로 단순화한다.

**Files:**
- Modify: `src/maia/agent_model.py`
- Modify: `src/maia/registry.py`
- Modify: `src/maia/cli_parser.py`
- Modify: `src/maia/cli.py`
- Test: `tests/test_cli.py`
- Modify: `README.md`

**Required changes:**
- `agent new <name>` creates an agent record with:
  - name
  - persona
  - user nickname/call-sign
  - lifecycle status
  - setup status = not-configured
- Remove model/provider/runtime-image requirements from the creation story.
- If extra metadata exists internally, do not surface it in the minimal public happy path.
- `agent list/status` should show whether the agent is not configured / ready / running.

**Validation:**
- `PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`

**Commit message:**
- `feat: simplify agent new identity flow`

---

## Task 106 — `agent setup` PTY passthrough for `hermes setup`

**Objective:** Maia가 agent별로 `hermes setup` interactive session을 붙여주는 기능을 구현한다.

**Files:**
- Create: `src/maia/agent_setup_session.py`
- Modify: `src/maia/cli_parser.py`
- Modify: `src/maia/cli.py`
- Modify: `src/maia/app_state.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_cli_runtime.py`
- Modify: `README.md`

**Required changes:**
- Add `maia agent setup <agent>`.
- Implementation contract:
  - prepare per-agent volume/home
  - launch setup-capable Hermes container/session
  - attach PTY/interactive stdio
  - run `hermes setup` inside agent context
  - return exit status to Maia
  - mark agent setup state as complete/incomplete
- Maia must not parse or rewrite the Hermes wizard.
- CLI-only support is acceptable for v1; document that gateway/chat surfaces do not support interactive setup.
- Failure messaging should say setup was interrupted/failed and must be rerun.

**Validation:**
- `PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`

**Commit message:**
- `feat: add agent setup passthrough for hermes setup`

---

## Task 107 — setup-gated `agent start|stop|status|logs`

**Objective:** setup 완료된 agent만 runtime으로 시작되고, runtime commands는 그 setup 결과를 사용한다.

**Files:**
- Modify: `src/maia/cli.py`
- Modify: `src/maia/docker_runtime_adapter.py`
- Modify: `src/maia/runtime_adapter.py`
- Modify: `src/maia/agent_model.py`
- Test: `tests/test_cli_runtime.py`
- Test: `tests/test_docker_runtime_adapter.py`
- Modify: `README.md`

**Required changes:**
- `agent start` preconditions:
  - infra setup completed
  - agent setup completed
- Runtime launch should mount/use the saved per-agent Hermes home/config volume.
- `agent status` should show setup state + runtime state.
- `agent logs` should clearly distinguish setup-not-done vs runtime-not-running.
- `agent stop` should remain simple operator flow.

**Validation:**
- `PYTHONPATH=src python3 -m pytest -q tests/test_cli_runtime.py tests/test_docker_runtime_adapter.py`

**Commit message:**
- `feat: gate runtime start on agent setup`

---

## Task 108 — docs/help/tests closeout and scope cleanup

**Objective:** public product story를 새 최소 흐름으로 닫고, 남은 군더더기를 정리한다.

**Files:**
- Modify: `README.md`
- Modify: `src/maia/cli_parser.py`
- Modify: `docs/prd/maia-core-product.md`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_cli_runtime.py`
- Modify: `docs/plans/phase15-minimal-agent-bootstrap-and-runtime-setup.md`

**Required changes:**
- README first-run section must read like:
  - install Maia
  - doctor
  - setup
  - agent new
  - agent setup
  - agent start
- Make it explicit that `agent setup` is interactive CLI-only passthrough to `hermes setup`.
- Remove leftover wording about team defaults, model override layers, Hermes auth checks in doctor, and Maia-managed setup wizard logic.
- Ensure examples do not imply Maia is a CLI messenger.

**Status:** completed via explicit first-run README section, operator-facing agent help wording, and CLI-only passthrough wording alignment across README/PRD/tests.

**Validation:**
- `PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `bash scripts/verify.sh`

**Commit message:**
- `docs: close minimal maia bootstrap flow`

---

## Verification bar
- task별 targeted pytest
- docs/help/tests alignment maintained
- real operator wording only
- `bash scripts/verify.sh`
- reviewer approve
- clean worktree at finish

## Acceptance criteria
- 일반 사용자는 `doctor → setup → agent new → agent setup → agent start` 흐름을 이해할 수 있다.
- `doctor`는 infra만 점검한다.
- `setup`은 shared infra만 준비한다.
- `agent new`는 identity creation으로 설명된다.
- `agent setup`은 실제 `hermes setup` interactive session을 붙여준다.
- setup 안 된 agent는 start되지 않는다.
- public docs/help가 더 이상 team defaults / override / Maia-managed Hermes wizard를 암시하지 않는다.
- public golden flow examples는 더 이상 `send/reply/inbox/thread`를 중심에 두지 않는다.
