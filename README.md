# Maia

Control plane for bringing up Maia shared infra, creating agent identities, opening per-agent Hermes setup, and operating agent runtime lifecycle.

## First run
Install Maia, then follow the Part 1 bootstrap path in this order:

1. `maia doctor`
2. `maia setup`
3. `maia agent new`
4. `maia agent setup <name>`
5. `maia agent start <name>`

`maia doctor` is the infra-only gate for this flow. It tells you whether to fix Docker, queue, or DB access first, or continue to `maia setup`.

`maia agent setup` is an interactive CLI-only passthrough to `hermes setup` for one agent. Maia does not replace or reinterpret the Hermes setup wizard.

Portable state and Keryx visibility stay available as support surfaces outside this first-run path.

## Part 1 operator flow
Maia Part 1 is an operator-facing bootstrap flow, not a messaging-first story. `maia doctor` is the first shared-infra decision point, and the rest of the bootstrap path follows only after it points you to `maia setup`.

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

## What each command means
- `maia doctor`: check shared infra readiness only: Docker, queue, and DB. If it passes, continue to `maia setup`; if it fails, fix shared infra and rerun `maia doctor`.
- `maia setup`: bootstrap shared infra only after `doctor` says the shared infra path is ready to continue.
- `maia agent new`: interactively create an agent identity by asking for agent name, how the agent addresses the user, and persona. New agents still carry the shared Hermes worker runtime defaults needed for first start.
- `maia agent setup <name>`: open `hermes setup` for that agent.
- `maia agent setup-gateway <name>`: reopen only the agent-scoped `hermes setup gateway` flow if messaging/home-channel setup was skipped the first time.
- `maia agent start|stop|status|logs <name>`: operate that agent after shared infra and agent setup are ready.
- `maia agent list|status` surface the overall launch-readiness state as `not-configured`, `ready`, or `running`.
- `maia agent status` also shows the recorded setup state (`not-started|complete|incomplete`) and current runtime state.
- agent setup is recorded separately from the runtime launch state.
- new agents carry the shared Hermes worker defaults needed for first start.

## Known limitations
- Runtime control (agent start|stop|status|logs) requires Docker CLI and a reachable Docker daemon.
- Shared infra depends on a reachable queue and DB state path.
- `maia setup` bootstraps the shared Maia network, RabbitMQ container, and SQLite state DB.
- The canonical Maia-owned SQLite file is `~/.maia/maia.db`.
- `maia agent setup` opens an interactive `hermes setup` session only in the CLI; gateway/chat surfaces do not support it.
- `maia agent start` now also requires gateway/home-channel setup to be complete; rerun `maia agent setup-gateway <name>` if that step was skipped.
- Keryx collaboration visibility stays on `thread`, `handoff`, and `workspace`; it is not the Part 1 bootstrap flow.

## Secondary surfaces
These remain public support workflows, but they are not the primary first-run bootstrap path.

- Portable state commands (`export`, `import`, `inspect`) remain available as operator support workflows.
- Keryx collaboration visibility commands (`thread`, `handoff`, `workspace`) remain available outside the Part 1 bootstrap story.

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
- The public Part 2 visibility story centers on `thread`, `handoff`, and `workspace` as Keryx-backed operator views of open collaboration state, recent handoffs, and participant runtime context.
- Keryx message delivery intent uses `delivery_mode`: `agent_only` keeps the exchange inside agent collaboration, `user_direct` targets direct user delivery, and a `user_direct` delivery failure is explicitly reported as `failed`.
- The target end state is multi-turn `request` / `question` / `answer` / `report` / `handoff` exchange rooted in Keryx collaboration state.

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

## Runtime support boundary
- Fake-docker tests verify Maia's runtime command flow, not whether Docker, the queue, or the DB work on this host.
- Run `maia doctor` before using `agent start|stop|status|logs` for real.
- Run `maia setup` to bootstrap shared infra before the first agent run.

## Live host runtime recovery
- If doctor fails, fix Docker, queue, or DB access first.
- If setup fails, finish shared infra bootstrap before retrying agent commands.
- If agent setup fails, rerun `maia agent setup <name>`.
- If start fails, rerun doctor and confirm shared infra is ready.

## V1 release checklist
- Top-level help and README lead with `doctor -> setup -> agent new -> agent setup -> agent start`.
- `doctor` stays infra-only: Docker, queue, and DB.
- `agent new` interactively captures agent name, user call-sign, and persona.
- `agent setup` is the operator path to open `hermes setup` for one agent.

## Development notes
- Codex CLI is used as the primary coding agent.
- This repository is initialized for iterative development.
- Docker is required for runtime control, and the Part 1 `maia doctor` contract is limited to shared infra readiness: Docker, queue, and DB.
- Harness watch policy v2 uses role-specific watch patterns via `scripts/codex-watch-patterns.sh`.
- Reviewer approval is read from a structured marker block and parsed with `python3 scripts/codex-parse-review.py <review-output-file>`.

## Registry persistence
- `JsonRegistryStorage` saves the agent registry as a single JSON object with an `agents` array.
- Missing registry files load as an empty `AgentRegistry`.
- Runtime CLI commands `maia export|import|inspect` operate on Maia portable state while Maia keeps one canonical SQLite DB at `~/.maia/maia.db` and the default registry path `~/.maia/registry.json` as the current portable source/target state.
- Part 3 portable-state mental model: export all by default, export to an explicit path when you want a named user/project snapshot, then import safely with preview + confirm.
- `maia export` without an explicit path writes a Maia bundle archive to `~/.maia/exports/maia-state.maia`.
- `maia export [path] --label <label> --description <text>` lets the operator write a user/project snapshot to an explicit path while keeping the same bundle/import contract and overriding manifest metadata.
- `maia import <path>` is the primary restore path for Maia portable state.
- `maia import <path> --preview` shows an import diff summary plus a risk classification line without mutating the current local registry.
- The preview also includes a `team` diff line so team-level portable metadata changes are visible before apply.
- Long preview value lists (`added`, `removed`, `changed`) truncate after 5 entries and append `...(+X)` while keeping the summary counts intact.
- Add `--verbose-preview` to print full added/removed/changed preview lists without truncation.
- `maia --help` and `maia import --help` describe the import safety flow directly: read-only preview, verbose preview expansion, and `--yes` overwrite-confirm skip behavior.
- Risk levels:
  - `safe`: no added, removed, or changed agents.
  - `low-change`: small non-destructive diffs, or imports into an empty current registry.
  - `high-impact`: destructive or broad diffs where the snapshots still share some agent identity overlap.
  - `replacement-like`: both sides are non-empty but share zero agent ids, so the import behaves like replacing one Maia team with another.
- Risk reason tokens:
  - `identical`
  - `current_empty`
  - `added_agents`
  - `removed_agents`
  - `changed_agents`
  - `changed_team_metadata`
  - `no_shared_agent_ids`
- `maia import <path>` always prints the preview/risk block first. When the current registry is non-empty or team-level portable metadata would be overwritten, it then performs a destructive-import preflight: warns about overwrite behavior and asks for confirmation.
- `maia import <path> --yes` skips the interactive confirmation but still prints the preview/risk summary and overwrite warning.
- `maia inspect <path>` is a secondary support command for pre-restore inspection; it is not required for the normal `maia export` + `maia import <path>` flow.
- `maia inspect <path>` inspects an importable Maia snapshot before restore and prints bundle format, manifest scope metadata, bundle label/version metadata, provenance metadata, agent names, status counts, and agent profile summaries.
- `maia team show` prints the current portable team metadata from `~/.maia/team.json` using the same encoded display format as inspect output.
- `maia team update ...` updates only team-level portable metadata (`team_name`, `team_description`, `team_tags`, `default_agent_id`) and never mutates agent persona/SOUL state.
- `maia handoff add|list|show` records and inspects thread-linked handoff pointers in collaboration state.
- `maia handoff add --thread-id <id> --from-agent <id> --to-agent <id> --type <type> --location <pointer> --summary <text>` validates that the thread exists, both agents exist, and both agents are already participants in that thread; it records only the pointer metadata and never auto-adds participants.
- `maia thread list` prints thread overview lines with `thread_id`, `topic`, `participants`, `participant_runtime`, `status`, `updated_at`, derived `pending_on`, `handoffs`, and `messages`; use `--agent <id>` or `--status <open|closed>` to filter.
- `maia thread show <thread_id>` prints the same summary plus `created_by`, `created_at`, recent handoff context (`recent_handoff_*`), and the stored message history for that thread; use `recent_handoff_id` with `maia handoff show <handoff_id>` to inspect the linked handoff.
- `maia handoff show <handoff_id>` prints the stored handoff pointer plus source/target workspace context lines derived from runtime spec data with `handoff_role`, `workspace_status`, `workspace_basis`, `workspace`, `runtime_image`, `runtime_command`, and `runtime_env_keys`; use the returned `agent_id` to continue with `workspace show`, `agent status`, or `agent logs`.
- `maia workspace show <agent_id>` prints the same `workspace_status` / `workspace_basis` contract for a single agent, plus `workspace`, `runtime_image`, `runtime_command`, and `runtime_env_keys`.
- The `.maia` bundle is a single zip-backed archive containing exactly one `manifest.json` and exactly one `registry.json` for the current v1 format.
- `maia import <path>` accepts either a `.maia` bundle archive, a raw registry JSON path, or a `manifest.json` path. When a manifest is provided, Maia resolves the referenced registry file from the same bundle directory.
- `~/.maia/exports/` is the portable snapshot area, while `~/.maia/runtime/` is reserved for runtime-only state that should not be treated as a portable backup.
- `maia agent start|stop <name>` updates the stored lifecycle status and prints the lightweight runtime signal returned by the configured runtime adapter (`runtime_status`, `runtime_handle`).
- `maia agent status <name>` confirms the stored/runtime status for the handoff source or target agent chosen from `thread show`, `handoff show`, or `workspace show`.
- `maia agent logs <name> --tail-lines <n>` tails recent runtime log lines for the same agent after the workspace/status check.
- `maia agent archive|restore <name>` updates only the stored lifecycle status and prints `updated agent_id=<id> status=<status>`.
- `maia agent tune <name> ...` updates agent persona/profile metadata in place. Supported flags now include persona (`--persona`, `--persona-file`), role (`--role`, `--clear-role`), model (`--model`, `--clear-model`), and tags (`--tags`, `--clear-tags`).
- `maia export <path>` writes a `.maia` single-file bundle when `<path>` ends with `.maia`; otherwise it writes the current registry JSON plus a sibling `manifest.json` for debugging/backcompat flows.
- `maia import <path>` replaces the current registry with the snapshot at `<path>` and preserves the stored agent order, lifecycle status, persona, role, model, and tags from that bundle.
- Portable agent profile metadata is now preserved in the registry/export/import contract:
  - `role`
  - `model`
  - `tags`
- Team-level metadata is now portable via manifest fields and restored on import:
  - `team_name`
  - `team_description`
  - `team_tags`
  - `default_agent_id`

## Operator examples
- Public examples use the installed `maia` entrypoint.
- Part 1 operator flow:
  - `maia doctor`
  - `maia setup`
  - `maia agent new`
  - `maia agent setup planner`
  - `maia agent start planner`
  - `maia agent status planner`
  - `maia agent logs planner --tail-lines 20`
  - `maia agent stop planner`
- Shared infra report format:
  - `doctor=ok|fail`
  - `setup=ok|fail`
  - `agent_setup=ok|fail`
  - `live_runtime_smoke=ok|fail`
- Secondary surfaces (not Part 1 bootstrap):
  - Portable state: `maia export`, `maia inspect <path>`, `maia import <path>`
- Primary Part 3 portable-state flow: `maia export`, `maia export <path>`, `maia import <path>`; use `maia inspect <path>` only as optional support when you want to inspect a snapshot before restore.
- Team metadata: `maia team show`, `maia team update ...`
- Collaboration visibility: `maia thread ...`, `maia handoff ...`, `maia workspace show ...`
- Delegation anchor contract: `user -> A -> B -> A -> user`

## Portable state scope
- Portable state kinds currently exported:
  - `registry`
  - `team-metadata`
  - `agent-profile-metadata`
- Runtime-only state kinds currently excluded from export/import:
  - `processes`
  - `locks`
  - `cache`
  - `live-sessions`
- The manifest records this boundary with:
  - `scope_version`
  - `portable_state_kinds`
  - `runtime_only_state_kinds`
- Current implemented scope_version is `3`, which packages the registry, team-level metadata, and portable agent profile metadata. In the canonical `.maia` archive form, that still means `manifest.json` + `registry.json` inside a single file, with team metadata carried in manifest fields and agent profile metadata carried in registry records.

## Portable state roadmap beyond the current scope
- The next recommended expansion is not live runtime state, but declarative launch intent beyond the already-implemented team metadata and agent profile slices.
- Recommended rollout order from here:
  1. agent launch defaults (`platform`, `working_directory`, `env_refs`, `disabled`)
- The current scope should continue excluding:
  - live processes
  - locks
  - caches
  - in-flight jobs
  - broker contents
  - transient logs
  - browser/session cookies
  - raw secret values
  - container ids / live Docker state
- See `docs/tasks/032-portable-state-v2-scope-planning.md` for the broader planning rationale, noting that team-level metadata and agent profile metadata from that plan are now implemented.
