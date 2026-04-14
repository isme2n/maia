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
- Runtime CLI commands `python -m maia agent new|list|status` use the default registry path `~/.maia/registry.json`.
