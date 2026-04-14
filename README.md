# Maia

Control plane for managing a team of Hermes agents with Docker, Compose, DB, and queue infrastructure.

## Development notes
- Codex CLI is used as the primary coding agent.
- This repository is initialized for iterative development.
- Docker is currently not installed on this server; install it before implementing/running container orchestration.

## Registry persistence
- `JsonRegistryStorage` saves the agent registry as a single JSON object with an `agents` array.
- Missing registry files load as an empty `AgentRegistry`.
