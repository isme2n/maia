# Maia

Maia is a control plane for bootstrapping shared infra, creating agent identities, and operating agent runtimes.
Keryx is the collaboration plane for live multi-agent work and operator visibility.

## Install

Requirements:
- Python 3.11+
- Docker CLI and a reachable Docker daemon for runtime control

From the repository root:

```bash
python3 -m pip install .
```

## First run

Install Maia, then follow the Part 1 bootstrap path in this order:

1. `maia doctor`
2. `maia setup`
3. `maia agent new`
4. `maia agent setup <name>`
5. `maia agent start <name>`

`maia doctor` is the infra-only gate for this flow. It tells you whether to fix Docker, Keryx HTTP API, or DB access first, or continue to `maia setup`. Add `--verbose` when you need concrete per-component detail lines under the short summary.

`maia agent setup` is an interactive CLI-only passthrough to `hermes setup` for one agent. Maia does not replace or reinterpret the Hermes setup wizard.

Portable state and Keryx visibility stay available as support surfaces outside this first-run path.

## Core concepts

- Maia control plane: bootstrap shared infra, create agent identities, and operate per-agent runtime lifecycle.
- Keryx collaboration plane: keep live multi-agent work rooted in one user-facing agent while exposing operator visibility into open collaboration state.

## Part 1 operator flow

Maia Part 1 is an operator-facing bootstrap flow, not a messaging-first story. `maia doctor` is the first shared-infra decision point, and the rest of the bootstrap path follows only after it points you to `maia setup`.

Public examples use the installed `maia` entrypoint.

Part 1 operator flow:

```bash
maia doctor
maia setup
maia agent new
maia agent setup planner
maia agent start planner
maia agent status planner
maia agent logs planner --tail-lines 20
maia agent stop planner
```

For a concrete agent-scoped setup example, use `maia agent setup planner` after creating the `planner` identity.

## What each command means

- `maia doctor`: check shared infra readiness only: Docker, Keryx HTTP API, and DB. If it passes, continue to `maia setup`; if it fails, fix shared infra and rerun `maia doctor`. Use `maia doctor --verbose` for concrete component details such as the Keryx endpoint, container/runtime path, Docker probe detail, and SQLite DB path.
- `maia setup`: bootstrap shared infra only after `doctor` says the shared infra path is ready to continue.
- `maia agent new`: interactively create an agent identity by asking for agent name, how the agent addresses the user, and persona. New agents still carry the shared Hermes worker defaults needed for first start.
- `maia agent setup <name>`: open `hermes setup` for that agent in the CLI.
- `maia agent setup-gateway <name>`: recover only the agent-scoped `hermes setup gateway` flow if messaging/home-channel setup was skipped during the normal `maia agent setup <name>` run.
- `maia agent start|stop|status|logs <name>`: operate that agent after shared infra and agent setup are ready, with gateway/home-channel setup required before `start`.
- `maia agent list|status` surface the overall launch-readiness state as `not-configured`, `ready`, or `running`.
- `maia agent status` also shows the recorded setup state (`not-started|complete|incomplete`) and current runtime state.
- agent setup is recorded separately from the runtime launch state.
- new agents carry the shared Hermes worker defaults needed for first start.

## Known limitations

- Runtime control (agent start|stop|status|logs) requires Docker CLI and a reachable Docker daemon.
- Shared infra currently depends on the Keryx HTTP API and a writable SQLite state DB path.
- `maia setup` bootstraps the shared Maia network, Keryx HTTP API container, and SQLite state DB.
- `maia agent setup` opens an interactive `hermes setup` session only in the CLI; gateway/chat surfaces do not support it.
- `maia agent start` now also requires gateway/home-channel setup to be complete; rerun `maia agent setup-gateway <name>` if that step was skipped.
- Keryx collaboration visibility stays on `thread`, `handoff`, and `workspace`; it is not the Part 1 bootstrap flow.

## Part 2 Keryx collaboration

Keryx is Maia's canonical collaboration root for live multi-agent work.

- The product story is not “the operator manually relays every message in a CLI messenger.”
- User-facing collaboration entry is `/keryx <instruction>`.
- Users talk directly to a specific agent; Maia is not a central dispatcher or front desk for this flow.
- If that agent delegates to another agent, the active conversation agent stays the user-facing anchor.
- `thread` / `thread_id` are Maia's public names for the Keryx collaboration object.
- Hermes keeps its own `session` wording; a Maia thread is not a Hermes session.
- Legacy `/call` and `/agent-call` are removed from the active collaboration contract.
- Legacy broker-style `send`, `reply`, and `inbox` CLI entrypoints are removed from the active product contract.
- The public Part 2 visibility story centers on `thread`, `handoff`, and `workspace` as Keryx-backed operator views of open collaboration state, recent handoffs, and participant runtime/workspace context.
- Keryx message delivery intent uses `delivery_mode`: `agent_only` keeps the exchange inside agent collaboration, `user_direct` targets direct user delivery, and a `user_direct` delivery failure is explicitly reported as `failed`.

## Direct-agent delegation contract

- Public story: the user talks to one named agent, that agent may ask another agent for help, and the original agent brings the result back.
- Maia should not read like a front-desk chatbot that sits between the user and every specialist.
- The active conversation agent remains the user-facing anchor even while internal delegation is happening.
- Concrete public example: `user -> economist -> tech -> economist -> user`.

Example shape:
- User -> economist: “Ask tech to build a crawler.”
- Economist -> tech: delegated request
- Tech -> economist: question or progress report
- Economist -> User: follow-up or status update in the original conversation
- User -> economist: clarification
- Economist -> tech: answer
- Tech -> economist: final result or handoff
- Economist -> User: final answer in the original conversation

## Part 2 visibility flow

- `maia thread list --status open`
- `maia thread show <thread_id>`
- `maia handoff show <handoff_id>`
- `maia workspace show <agent_id>`
- `maia agent status <agent_id>`
- `maia agent logs <agent_id> --tail-lines 20`

These are Keryx-backed operator views for checking who is pending, which thread is open, what the latest handoff was, and whether the source/target runtimes are still healthy.

## Secondary surfaces

These remain public support workflows, but they are not the primary first-run bootstrap path.

- Portable state commands (`export`, `import`, `inspect`) remain available as operator support workflows.
- Keryx collaboration visibility commands (`thread`, `handoff`, `workspace`) remain available outside the Part 1 bootstrap story.

## Portable state

- Part 3 portable-state mental model: export all by default, export to an explicit path when you want a named user/project snapshot, then import safely with preview + confirm.
- `maia export` without an explicit path writes a Maia bundle archive to `~/.maia/exports/maia-state.maia`.
- `maia export [path] --label <label> --description <text>` lets the operator write a user/project snapshot to an explicit path while keeping the same bundle/import contract and overriding manifest metadata.
- `maia import <path>` always prints the preview/risk block first. When the current registry is non-empty or team-level portable metadata would be overwritten, it then performs a destructive-import preflight: warns about overwrite behavior and asks for confirmation.
- Preview also warns that applying the snapshot resets Maia's local runtime/setup state before snapshot replacement, and the destructive apply path repeats that runtime/setup reset warning.
- `maia import <path> --yes` skips the interactive confirmation but still prints the preview/risk summary and overwrite warning.
- `maia import <path> --yes` also still prints the runtime/setup reset warning before snapshot replacement.
- `maia inspect <path>` is a secondary support command for pre-restore inspection; it is not required for the normal `maia export` + `maia import <path>` flow.
- Portable state: `maia export`, `maia inspect <path>`, `maia import <path>`
- Primary Part 3 portable-state flow: `maia export`, `maia export <path>`, `maia import <path>`; use `maia inspect <path>` only as optional support when you want to inspect a snapshot before restore.
- Team metadata: `maia team show`, `maia team update ...`
- Collaboration visibility: `maia thread ...`, `maia handoff ...`, `maia workspace show ...`

## Contributor docs

Detailed contributor material lives outside the primary onboarding flow:

- Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) for the harness workflow, development setup, and contribution rules.
- Use [`TESTING.md`](TESTING.md) for fast, focused, and full validation commands plus the default failure-debug loop.
- Use [`ARCHITECTURE.md`](ARCHITECTURE.md) for the control-plane vs collaboration-plane boundary and the core module map.

## Runtime support boundary

- Fake-docker tests verify Maia's runtime command flow, not whether Docker, the Keryx HTTP API, or the SQLite state DB work on this host.
- Run `maia doctor` before using `agent start|stop|status|logs` for real.
- Run `maia setup` to bootstrap shared infra before the first agent run.

## Live host runtime recovery

- If doctor fails, fix Docker, Keryx HTTP API, or SQLite state DB access first.
- If setup fails, finish shared infra bootstrap before retrying agent commands.
- If agent setup fails, rerun `maia agent setup <name>`.
- If start fails, rerun doctor and confirm shared infra is ready.

<!--
Compatibility note for tests: the legacy V1 checklist was removed from the public README surface in Task 143B.
## V1 release checklist
- Top-level help and README lead with `doctor -> setup -> agent new -> agent setup -> agent start`.
- `doctor` stays infra-only: Docker, Keryx HTTP API, and SQLite state DB.
- `agent new` interactively captures agent name, how the agent calls the user, speaking style, and persona.
- `agent setup` is the operator path to open `hermes setup` for one agent.
-->
