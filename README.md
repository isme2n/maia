# Maia

Control plane for managing a team of Hermes agents with Docker, Compose, DB, and queue infrastructure.

## Development notes
- Codex CLI is used as the primary coding agent.
- This repository is initialized for iterative development.
- Docker is required for runtime control, and `maia doctor` now checks both Docker readiness and optional broker readiness via `MAIA_BROKER_URL`.
- Harness watch policy v2 uses role-specific watch patterns via `scripts/codex-watch-patterns.sh`.
- Reviewer approval is read from a structured marker block and parsed with `python3 scripts/codex-parse-review.py <review-output-file>`.

## Registry persistence
- `JsonRegistryStorage` saves the agent registry as a single JSON object with an `agents` array.
- Missing registry files load as an empty `AgentRegistry`.
- Runtime CLI commands `python -m maia export|import|inspect` operate on Maia portable state using the default registry path `~/.maia/registry.json` as the current source/target state.
- `python -m maia export` without an explicit path writes a Maia bundle archive to `~/.maia/exports/maia-state.maia`.
- `python -m maia export [path] --label <label> --description <text>` lets the operator override manifest metadata while keeping the same bundle/import contract.
- `python -m maia import <path> --preview` shows an import diff summary plus a risk classification line without mutating the current local registry.
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
- `python -m maia import <path>` always prints the preview/risk block first. When the current registry is non-empty or team-level portable metadata would be overwritten, it then performs a destructive-import preflight: warns about overwrite behavior and asks for confirmation.
- `python -m maia import <path> --yes` skips the interactive confirmation but still prints the preview/risk summary and overwrite warning.
- `python -m maia inspect <path>` inspects an importable Maia snapshot before restore and prints bundle format, manifest scope metadata, bundle label/version metadata, provenance metadata, agent names, status counts, and agent profile summaries.
- `python -m maia team show` prints the current portable team metadata from `~/.maia/team.json` using the same encoded display format as inspect output.
- `python -m maia team update ...` updates only team-level portable metadata (`team_name`, `team_description`, `team_tags`, `default_agent_id`) and never mutates agent persona/SOUL state.
- `python -m maia artifact add|list|show` manages thread-linked artifact metadata using the existing `HandoffRecord` storage model while keeping the public CLI wording on `artifact`.
- `python -m maia artifact add --thread-id <id> --from-agent <id> --to-agent <id> --type <type> --location <pointer> --summary <text>` validates that the thread exists, both agents exist, and both agents are already participants in that thread; it never auto-adds participants.
- The `.maia` bundle is a single zip-backed archive containing exactly one `manifest.json` and exactly one `registry.json` for the current v1 format.
- `python -m maia import <path>` accepts either a `.maia` bundle archive, a raw registry JSON path, or a `manifest.json` path. When a manifest is provided, Maia resolves the referenced registry file from the same bundle directory.
- `~/.maia/exports/` is the portable snapshot area, while `~/.maia/runtime/` is reserved for runtime-only state that should not be treated as a portable backup.
- `python -m maia agent start|stop|archive|restore <agent_id>` only updates the stored registry status and prints `updated agent_id=<id> status=<status>`.
- `python -m maia agent tune <agent_id> ...` updates agent persona/profile metadata in place. Supported flags now include persona (`--persona`, `--persona-file`), role (`--role`, `--clear-role`), model (`--model`, `--clear-model`), and tags (`--tags`, `--clear-tags`).
- `python -m maia export <path>` writes a `.maia` single-file bundle when `<path>` ends with `.maia`; otherwise it writes the current registry JSON plus a sibling `manifest.json` for debugging/backcompat flows.
- `python -m maia import <path>` replaces the current registry with the snapshot at `<path>` and preserves the stored agent order, lifecycle status, persona, role, model, and tags from that bundle.
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
- Check local Docker/runtime and broker readiness:
  - `python -m maia doctor`
- Broker-backed smoke path:
  - `export MAIA_BROKER_URL=amqp://user:<password>@host:5672/%2F`
  - `python -m maia send <from_agent_id> <to_agent_id> --body 'hello' --topic 'smoke'`
  - `python -m maia inbox <to_agent_id>`
  - verify `source=broker` and ack policy in the output
- Record and inspect a thread-linked artifact handoff:
  - `python -m maia artifact add --thread-id <thread_id> --from-agent <from_agent_id> --to-agent <to_agent_id> --type report --location reports/phase7.md --summary 'Phase 7 review bundle'`
  - `python -m maia artifact list --thread-id <thread_id>`
  - `python -m maia artifact show <artifact_id>`
- Default export bundle:
  - `python -m maia export`
- Inspect a bundle before import:
  - `python -m maia inspect ~/.maia/exports/maia-state.maia`
- Show current team metadata:
  - `python -m maia team show`
- Update team metadata safely:
  - `python -m maia team update --name research-lab --description 'Nightly migration team' --tags research,ops --default-agent <agent_id>`
- Tune agent profile metadata:
  - `python -m maia agent tune <agent_id> --role researcher --model gpt-5 --tags runtime,focus`
- Clear agent profile metadata fields:
  - `python -m maia agent tune <agent_id> --clear-role --clear-model --clear-tags`
- Clear optional team metadata fields:
  - `python -m maia team update --clear-description --clear-tags --clear-default-agent`
- Preview an import without changing local state:
  - `python -m maia import backups/team.maia --preview`
- Preview large imports with full details:
  - `python -m maia import backups/team.maia --preview --verbose-preview`
- Apply a reviewed import without interactive confirmation:
  - `python -m maia import backups/team.maia --yes`

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
