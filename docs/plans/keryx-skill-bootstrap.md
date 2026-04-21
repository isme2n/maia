# Keryx skill bootstrap

## Scope
- Materialize a built-in Hermes skill file for Maia's `/keryx <freeform instruction>` collaboration entrypoint.
- Seed it into each agent-scoped Hermes home on `maia agent new`.
- Refresh it around `run_agent_setup_session(...)` so setup cannot permanently remove or stale it.
- Backfill it on `maia agent start` for older agents missing the skill.
- Validate bootstrap/install behavior plus the embedded skill contract for grounded Keryx HTTP execution guidance.

## Narrow design
- Keep the built-in skill content embedded in `src/maia/keryx_skill.py`.
- Expose deterministic install helpers keyed off the agent-scoped Hermes home.
- Call the installer from the three lifecycle touchpoints: new, setup, start.
- Cover the lifecycle with focused CLI/session tests that assert the skill file exists and still advertises `/keryx` guidance.

## Validation
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/test_cli.py`
