# Maia

Control plane for managing a team of Hermes agents with Docker, Compose, DB, and queue infrastructure.

## Development notes
- Codex CLI is used as the primary coding agent.
- This repository is initialized for iterative development.
- Docker is currently not installed on this server; install it before implementing/running container orchestration.
- Harness watch policy v2 uses role-specific watch patterns via `scripts/codex-watch-patterns.sh`.
- Reviewer approval is read from a structured marker block and parsed with `python3 scripts/codex-parse-review.py <review-output-file>`.

## Registry persistence
- `JsonRegistryStorage` saves the agent registry as a single JSON object with an `agents` array.
- Missing registry files load as an empty `AgentRegistry`.
- Runtime CLI commands `python -m maia agent new|start|stop|archive|restore|list|status|tune|export|import` use the default registry path `~/.maia/registry.json`.
- `python -m maia agent export` without an explicit path writes a portable snapshot to `~/.maia/exports/registry.json`.
- `~/.maia/exports/` is the portable snapshot area, while `~/.maia/runtime/` is reserved for runtime-only state that should not be treated as a portable backup.
- `python -m maia agent start|stop|archive|restore <agent_id>` only updates the stored registry status and prints `updated agent_id=<id> status=<status>`.
- `python -m maia agent tune <agent_id> --persona <text>` or `--persona-file <path>` updates only the stored persona string and keeps the existing agent id, name, and status unchanged. Exactly one persona source is required.
- `python -m maia agent export <path>` writes the current registry JSON to a portable plain JSON path and creates missing parent directories.
- `python -m maia agent import <path>` replaces the current registry with the JSON at `<path>` and preserves the stored agent order, statuses, and personas from that file.
