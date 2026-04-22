# Maia Init One-Command Onboarding Plan

> For Hermes: use the Codex harness loop task-by-task. Each task must have its own scoped spec, validation, and reviewer approval.

Goal: Make Maia feel like a one-command OSS CLI tool: install, run `maia init`, and end in a truthful conversation-ready state with a running Docker-backed agent and at least one usable user-facing gateway.

Architecture:
- Keep Maia as the control plane and Keryx as the collaboration plane.
- Do not sniff, parse, or reimplement Hermes setup internals. Use agent-scoped passthrough/attach/relay for real Hermes setup, then record only readiness state.
- Public happy path becomes `maia init`; advanced/operator commands remain available as decomposed escape hatches.

Tech stack:
- Existing Python CLI (`maia` entrypoint)
- Existing Docker/Keryx/SQLite shared infra
- Existing agent-scoped Hermes homes and runtime worker model
- Existing gateway readiness state model (`complete` / `token-only` / `incomplete`)

---

## Product contract to lock

### Public happy path
- Try now:
  - `uvx maia init`
  - later optional alternatives: `pipx run maia init`, `pipx install maia`, `brew install maia`
- Installed usage:
  - `maia init`

### What `maia init` must guarantee on success
1. Shared infra ready
2. First agent identity exists
3. Real Hermes setup for that agent completed through passthrough flow
4. At least one usable user-facing gateway is configured (platform-agnostic, not Telegram-specific)
5. A default delivery/chat destination is resolvable
6. The first agent runtime is actually started in Docker
7. Final state is conversation-ready now, not merely partially configured

### Explicit non-goals for v1 init
- Reimplementing Hermes setup questions inside Maia
- Sniffing Hermes setup prompt semantics
- Introducing a dashboard-first flow ahead of CLI bootstrap
- Supporting every gateway equally in the first implementation if one generic abstraction can cover multiple adapters

### First-run UX principles
- One public command to remember: `maia init`
- Ask only the smallest identity questions first:
  - agent name
  - how the agent addresses the user
  - persona
  - optional speaking style if already part of current identity flow
- Keep advanced provider/runtime/gateway detail behind passthrough or guided follow-ups
- End every successful run with one next action only: start talking now
- End every failed run with one clear remediation and a resume path

### Control-plane rule
- Maia orchestrates setup, readiness, lifecycle, and recovery.
- Hermes owns its own setup UX.
- Maia may launch and relay Hermes setup IO, but must not interpret it as product logic.

---

## Recommended implementation sequence

### Task 152 — Public contract and packaging story lock
Objective: align README/help/package metadata around `maia init` as the public happy path without yet wiring full implementation.

Files:
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `src/maia/cli_parser.py`
- Modify: `tests/test_cli.py`
- Create: `docs/tasks/152-maia-init-public-contract-and-packaging.md`

Deliverables:
- quickstart rewritten around `uvx maia init` / `maia init`
- package description no longer says skeleton
- help text explains `init` as the canonical onboarding path
- old decomposed flow remains documented as advanced/operator flow

### Task 153 — Init state model and CLI surface skeleton
Objective: add the `maia init` command surface and the explicit conversation-ready/partial-failure state model.

Files:
- Modify: `src/maia/cli_parser.py`
- Modify: `src/maia/cli.py`
- Modify: `tests/test_cli.py`
- Create: `docs/tasks/153-maia-init-cli-surface-and-state-model.md`

Deliverables:
- `maia init` command exists
- dry-run/status text clearly distinguishes:
  - infra ready
  - agent setup ready
  - gateway ready
  - destination ready
  - runtime running
  - conversation ready
- `maia init --resume` contract introduced if needed

### Task 154 — Init orchestration for shared infra + agent identity + real Hermes passthrough
Objective: make `maia init` orchestrate doctor/setup/new/agent setup truthfully, without sniffing Hermes setup.

Files:
- Modify: `src/maia/cli.py`
- Modify: `src/maia/agent_setup_session.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_cli_runtime.py`
- Create: `docs/tasks/154-maia-init-orchestrates-real-hermes-setup.md`

Deliverables:
- `maia init` can create first agent identity if missing
- `maia init` launches real agent-scoped Hermes setup passthrough
- setup outcome is recorded as readiness only
- no duplicated Hermes setup questionnaire logic inside Maia

### Task 155 — Gateway-agnostic readiness and default destination inside init
Objective: absorb gateway setup into init as a generic readiness requirement rather than a Telegram-specific branch.

Files:
- Modify: `src/maia/cli.py`
- Modify: `src/maia/agent_setup_session.py`
- Modify: `src/maia/cli_parser.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_cli_runtime.py`
- Create: `docs/tasks/155-maia-init-gateway-agnostic-readiness.md`

Deliverables:
- init asks for/recovers at least one usable gateway in a platform-agnostic way
- init records whether a usable default delivery target exists
- no public wording hardcodes Telegram as the product contract
- decomposed recovery commands can remain, but public happy path does not depend on users memorizing them

### Task 156 — Conversation-ready completion: start Docker agent and verify runnable-now state
Objective: finish init by starting the first agent in Docker and verifying actual conversation-ready status.

Files:
- Modify: `src/maia/cli.py`
- Modify: `src/maia/docker_runtime_adapter.py` (only if needed by spec)
- Modify: `tests/test_cli_runtime.py`
- Modify: `README.md`
- Create: `docs/tasks/156-maia-init-conversation-ready-start.md`

Deliverables:
- init success means the agent runtime actually started
- final messaging says ready now / action needed, not vague setup-complete wording
- init failure surfaces exact remediation and resume command

### Task 157 — End-to-end closeout and release-readiness pass for OSS onboarding
Objective: verify the whole one-command path on real host constraints and align docs/help/tests for open-source release.

Files:
- Modify: `README.md`
- Modify: `docs/prd/maia-core-product.md`
- Modify: `docs/plans/maia-product-roadmap-5-parts.md` if needed
- Modify: scoped help/tests files as needed
- Create: `docs/tasks/157-maia-init-closeout-and-release-readiness.md`

Deliverables:
- end-to-end validated `maia init` story
- explicit repo-level vs host-level proof recorded
- final quickstart wording aligned across README/help/tests

---

## Design constraints to preserve in every task
- Never sniff or reverse-engineer Hermes setup semantics
- Never claim success before gateway + destination + runtime are actually usable
- Keep public wording platform-agnostic (`gateway`, `chat surface`, `default destination`) unless a task is explicitly adapter-specific
- Preserve advanced/operator commands; do not hide recovery paths from power users
- Prefer narrow task scopes and harness-friendly validation

---

## Recommended validation progression
- Start each task with focused tests only
- After each worker run, re-run task-local validation yourself
- After every 1–2 tasks, run the broader related suites
- Before open-source release work, run:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
  - any task-specific focused suites
  - real host smoke where possible

---

## Success definition for the whole plan
A new OSS user should be able to understand the product by reading only the first screen of the README and then do this:

1. `uvx maia init`
2. answer a few questions
3. finish real Hermes passthrough setup
4. get one usable gateway/destination bound
5. have the first agent actually running in Docker
6. talk immediately

If that is not true, the onboarding is not finished.
