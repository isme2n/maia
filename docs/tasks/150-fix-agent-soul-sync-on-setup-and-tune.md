# Task 150 — fix agent SOUL sync on setup and tune

## Goal
- Close the regression where Maia agents still introduce themselves as default Hermes after `agent setup` / `agent tune`, even though agent record identity fields (name, call_sign, speaking_style, persona) are stored correctly.
- Ensure agent-scoped `hermes/SOUL.md` is synced from the Maia registry identity so direct Telegram DM responses use the configured persona/identity.

## Root-cause evidence
- Live agent records in `~/.maia/maia.db` already contain the right values for `다` / `토모`:
  - name, call_sign, speaking_style, persona are populated.
- Live agent-scoped files still show default Hermes SOUL:
  - `/home/asle/.maia/agents/<agent_id>/hermes/SOUL.md`
  - first line is still `You are Hermes Agent...`
- Current `src/maia/hermes_runtime_worker.py` already builds Keryx worker prompts with agent-first wording, so the direct DM regression path is the Hermes SOUL used by gateway chat sessions.
- Current `src/maia/cli.py` does not sync/write agent identity into `SOUL.md` after `agent setup` or `agent tune`.

## Non-goals
- Rework Hermes gateway onboarding or home-channel prompts
- Change runtime worker prompt wording
- Broaden agent identity schema again
- Add new CLI commands

## Allowed files
- `src/maia/cli.py`
- `tests/test_cli.py`
- `docs/tasks/150-fix-agent-soul-sync-on-setup-and-tune.md`

## Acceptance criteria
- [ ] Maia has a dedicated helper that renders agent identity text for agent-scoped `hermes/SOUL.md` using agent-first wording.
- [ ] Successful `maia agent setup <name>` syncs the agent SOUL into the agent-scoped Hermes home after setup completes.
- [ ] Successful `maia agent tune <name> ...` re-syncs the agent SOUL when the agent-scoped Hermes home already exists.
- [ ] Synced SOUL includes, at minimum:
  - `You are {agent_name}.`
  - `Call the user "{call_sign}".`
  - speaking style line
  - optional custom speaking-style details line when applicable
  - persona line when set
- [ ] Focused pytest coverage locks both setup-time sync and tune-time sync.

## Required validation commands
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py`
- `cd /home/asle/maia && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_hermes_runtime_worker.py`

## Forbidden changes
- No changes outside allowed files
- No gateway bridge/auth changes
- No Docker/runtime adapter changes
- No broad CLI help or parser cleanup unrelated to SOUL sync

## Notes
- Keep the wording aligned with the already-passing runtime worker prompt style:
  - `You are {agent_name}.`
  - `Call the user "{call_sign}".`
- This repo is already dirty; reviewer must judge only this task scope.
