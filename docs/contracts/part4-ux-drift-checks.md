# Part 4 UX Drift Checks

Run from the repo root. The help checks below use the module-entrypoint form (`python3 -m maia`). If the current interpreter does not resolve `maia`, rerun in an environment where Maia is installed or importable (for example `PYTHONPATH=src`).

## Text checks

```bash
# Primary first-run/bootstrap order stays fixed in README + help constants.
rg -n 'Top-level help and README lead with `doctor -> setup -> agent new -> agent setup -> agent start`\.' README.md
rg -n 'Top-level help and README lead with `doctor -> setup -> agent new -> agent setup -> agent start`\.' src/maia/cli_parser.py
rg -n '^1\. `maia doctor`$' README.md
rg -n '^2\. `maia setup`$' README.md
rg -n '^3\. `maia agent new`$' README.md
rg -n '^4\. `maia agent setup <name>`$' README.md
rg -n '^5\. `maia agent start <name>`$' README.md
rg -n 'assert "Install Maia, then follow the Part 1 bootstrap path in this order" in text' tests/test_cli.py
rg -n 'assert "Part 1 operator flow:" in captured\.out' tests/test_cli.py
rg -n 'for line in V1_RELEASE_CHECKLIST:' tests/test_cli.py

# doctor/setup/agent core flow wording stays split by responsibility.
rg -n '^- `maia doctor`: check shared infra readiness only: Docker, queue, and DB\.' README.md
rg -n '^- `maia setup`: bootstrap shared infra only' README.md
rg -n '^- `maia agent new`: interactively create an agent identity by asking for agent name, how the agent addresses the user, and persona\.' README.md
rg -n '^`maia agent setup` is an interactive CLI-only passthrough to `hermes setup` for one agent\.' README.md
rg -n '^- `maia agent start\|stop\|status\|logs <name>`: operate that agent after shared infra and agent setup are ready\.$' README.md
rg -n 'Check shared infra readiness \(Docker, queue, DB\)' src/maia/cli_parser.py
rg -n 'Check shared infra readiness for Docker, queue, and DB access only\.' src/maia/cli_parser.py
rg -n 'assert "Check shared infra readiness" in captured\.out' tests/test_cli.py
rg -n 'Bootstrap shared Maia infra \(Docker, queue, DB\)' src/maia/cli_parser.py
rg -n 'Bootstrap shared Maia infra only: Docker-backed services, queue, and DB state\.' src/maia/cli_parser.py
rg -n 'assert "Bootstrap shared Maia infra" in captured\.out' tests/test_cli.py
rg -n 'Interactively create an agent identity with name, user call-sign, and persona\.' src/maia/cli_parser.py
rg -n 'assert "Interactively create an agent identity" in captured\.out' tests/test_cli.py
rg -n 'Open hermes setup for an agent in the CLI and keep the shared Hermes worker defaults for first start\.' src/maia/cli_parser.py
rg -n 'assert "Open hermes setup for an agent" in captured\.out' tests/test_cli.py
rg -n 'Start an agent runtime after shared infra and agent setup are ready\.' src/maia/cli_parser.py
rg -n 'assert "Start an agent runtime after shared infra and agent setup are ready\." in captured\.out' tests/test_cli.py
rg -n 'Next: run maia agent new' src/maia/cli.py
rg -n 'Next: run maia agent setup ' src/maia/cli.py
rg -n 'Next: run maia agent start ' src/maia/cli.py
rg -n 'assert "Next: run maia agent new" in captured\.out' tests/test_cli.py
rg -n 'assert "Next: run maia agent setup econ" in captured\.out' tests/test_cli.py
rg -n 'assert "run maia agent start planner" in captured\.out' tests/test_cli.py
rg -n 'shared infra setup is not complete' src/maia/cli.py
rg -n 'agent setup is not complete' src/maia/cli.py

# doctor/setup must not drift into provider/login/model-default bootstrap wording.
if python3 -m maia doctor --help | rg -n 'provider|login|model'; then
  echo 'doctor help drifted beyond infra-only scope'
  exit 1
fi
if python3 -m maia setup --help | rg -n 'team defaults|model defaults|wizard'; then
  echo 'setup help drifted beyond shared-infra scope'
  exit 1
fi

# Part 3 portable-state wording stays present, but secondary to Part 4 bootstrap.
rg -n '^- Portable state commands \(`export`, `import`, `inspect`\) remain available as operator support workflows\.$' README.md
rg -n 'Primary Part 3 flow: `maia export` saves the full portable snapshot to `~/.maia/exports/maia-state.maia` by default\.' src/maia/cli_parser.py
rg -n '"Primary Part 3 flow: `maia export` saves the full portable snapshot to "' tests/test_cli.py
rg -n '`maia import <path>` restores safely: preview first, confirm before destructive apply, use `--yes` to skip confirmation\.' src/maia/cli_parser.py
rg -n '"`maia import <path>` restores safely: preview first, confirm before "' tests/test_cli.py
rg -n '`maia inspect <path>` is an optional support command, not a required part of the normal save/restore flow\.' src/maia/cli_parser.py
rg -n '"`maia inspect <path>` is an optional support command, not a required "' tests/test_cli.py
rg -n '`maia inspect <path>` is a secondary support command for pre-restore inspection; it is not required for the normal `maia export` \+ `maia import <path>` flow\.' README.md
rg -n 'assert "`maia inspect <path>` is a secondary support command for pre-restore inspection; it is not required for the normal `maia export` \+ `maia import <path>` flow\." in readme' tests/test_cli.py
if rg -n 'Primary Part 3 portable-state flow: `maia export`, `maia inspect <path>`, `maia import <path>`' \
  README.md; then
  echo 'inspect drifted into the primary portable-state flow'
  exit 1
fi

# Keryx visibility stays secondary/support, not bootstrap.
rg -n 'Keryx collaboration visibility stays on `thread`, `handoff`, and `workspace`; it is not the Part 1 bootstrap flow\.' README.md
rg -n 'Keryx collaboration visibility stays on `thread`, `handoff`, and `workspace`; it is not the Part 1 bootstrap flow\.' src/maia/cli_parser.py
rg -n '^- Collaboration visibility: `maia thread \.\.\.`, `maia handoff \.\.\.`, `maia workspace show \.\.\.`$' \
  README.md
```

## Help checks

```bash
python3 -m maia --help | rg -n '^Part 1 operator flow:$'
python3 -m maia --help | rg -n '^  maia doctor$'
python3 -m maia --help | rg -n '^  maia setup$'
python3 -m maia --help | rg -n '^  maia agent new$'
python3 -m maia --help | rg -n '^  maia agent setup planner$'
python3 -m maia --help | rg -n '^  maia agent start planner$'
python3 -m maia --help | rg -n '^Portable state flow:$'
python3 -m maia --help | rg -n '^Keryx operator visibility flow:$'
if python3 -m maia --help | rg -n '`maia inspect <path>` is the primary restore flow'; then
  echo 'top-level help drifted: inspect is shown as primary'
  exit 1
fi

python3 -m maia doctor --help | rg -n 'Check shared infra readiness for Docker, queue, and DB access only\.'
python3 -m maia doctor --help | rg -n '^  maia doctor$'
if python3 -m maia doctor --help | rg -n 'provider|login|wizard'; then
  echo 'doctor help drifted beyond infra-only wording'
  exit 1
fi

python3 -m maia setup --help | rg -n 'Bootstrap shared Maia infra only: Docker-backed services, queue, and DB state\.'
python3 -m maia setup --help | rg -n '^  maia setup$'
if python3 -m maia setup --help | rg -n 'team defaults|model defaults|provider'; then
  echo 'setup help drifted beyond shared-infra wording'
  exit 1
fi

python3 -m maia agent --help | rg -n 'Create an agent identity'
python3 -m maia agent --help | rg -n 'Open hermes setup for an agent in the CLI'
python3 -m maia agent --help | rg -n 'Reopen hermes setup gateway for an agent in the CLI'
python3 -m maia agent --help | rg -n 'Start an agent runtime'
```

## Test checks

```bash
python3 -m pytest -q tests/test_cli.py

python3 -m pytest -q \
  tests/test_cli.py::test_readme_locks_part1_public_flow \
  tests/test_cli.py::test_top_level_help \
  tests/test_cli.py::test_doctor_help_includes_examples \
  tests/test_cli.py::test_setup_help_includes_examples \
  tests/test_cli.py::test_agent_new_help_describes_identity_only_flow \
  tests/test_cli.py::test_agent_setup_help_includes_examples \
  tests/test_cli.py::test_agent_runtime_help_uses_operator_wording \
  tests/test_cli.py::test_agent_start_help_describes_part1_prerequisites \
  tests/test_cli.py::test_readme_examples_align_with_public_help

python3 -m pytest -q \
  tests/test_cli.py::test_setup_command_prints_bootstrap_summary_from_infra_runtime \
  tests/test_cli.py::test_agent_new_prompts_for_identity_fields_and_points_to_agent_setup \
  tests/test_cli.py::test_agent_setup_command_runs_hermes_setup_and_records_complete \
  tests/test_cli.py::test_import_help_describes_safety_flags \
  tests/test_cli.py::test_inspect_help_includes_examples \
  tests/test_cli.py::test_export_help_includes_examples
```
