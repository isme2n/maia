# Maia Architecture

This document is a concise map for contributors. Product onboarding stays in `README.md`, and contribution workflow stays in `CONTRIBUTING.md`.

## Boundary

- Maia is the control plane: it bootstraps shared infra, manages agent identity, stores portable state, and operates agent runtime lifecycle.
- Keryx is the collaboration plane: it tracks open threads, handoffs, workspace visibility, and the state around live multi-agent work.
- Active shared infra for the public bootstrap path is Docker, the Keryx HTTP API, and the SQLite state DB.
- Maia should not read like a central front desk relaying every live message. The user-facing anchor is one named agent; collaboration surfaces expose the surrounding state.

In practice, Part 1 first-run flow is control-plane-first, while `thread`, `handoff`, and `workspace` are collaboration-plane visibility surfaces.

## Major module map

Control plane and runtime:
- `src/maia/main.py`, `src/maia/cli_parser.py`, `src/maia/cli.py`: CLI entrypoint, public command contract, and command dispatch.
- `src/maia/agent_model.py`, `src/maia/registry.py`, `src/maia/storage.py`, `src/maia/sqlite_state.py`, `src/maia/team_metadata.py`, `src/maia/app_state.py`: persisted control-plane state.
- `src/maia/bundle_archive.py`, `src/maia/backup_manifest.py`: portable export/import/inspect surfaces.
- `src/maia/runtime_spec.py`, `src/maia/runtime_adapter.py`, `src/maia/docker_runtime_adapter.py`, `src/maia/runtime_state_storage.py`, `src/maia/infra_runtime.py`, `src/maia/agent_setup_session.py`: shared infra checks, runtime lifecycle, and agent-scoped setup.

Collaboration plane:
- `src/maia/keryx_models.py`, `src/maia/keryx_storage.py`, `src/maia/keryx_service.py`, `src/maia/keryx_server.py`, `src/maia/keryx_skill.py`: Keryx thread, handoff, pending-work, and visibility surfaces.
- `src/maia/message_model.py`, `src/maia/handoff_model.py`: shared collaboration record types used by the active Keryx-backed flow.

## Reading order

If you are new to the codebase, read in this order:

1. `README.md` for the public contract.
2. `src/maia/cli_parser.py` and `src/maia/cli.py` for the surfaced behavior.
3. Control-plane storage/runtime modules for bootstrap and lifecycle behavior.
4. Keryx service/storage/model modules for collaboration state and operator visibility.
