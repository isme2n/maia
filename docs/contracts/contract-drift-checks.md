# Contract Drift Checks

Run from the repo root. The help checks below use the module-entrypoint form (`python3 -m maia`). If the current interpreter does not resolve `maia`, rerun with an environment where Maia is installed or importable (for example `PYTHONPATH=src`).

## Text checks

```bash
# /keryx stays the explicit instruction contract.
rg -n '/keryx' src/maia/keryx_skill.py tests/test_cli.py

# /call and /agent-call are removed from the active contract.
# Negative wording that says they are removed is allowed, but active command examples are forbidden.
rg -n 'Legacy `/call` and `/agent-call` are removed from the active collaboration contract\.' \
  README.md src/maia/cli_parser.py tests/test_cli.py

# Forbid active command usage examples that would revive legacy entrypoints.
if rg -n '(^|\s)(maia\s+call\b|/call\s+\S|/agent-call\s+\S)' README.md src/maia/cli_parser.py tests/test_cli.py; then
  echo 'Unexpected active /call or /agent-call contract example'
  exit 1
fi

# Legacy negative mention remains allowed in the embedded skill.
rg -n '/call|/agent-call' src/maia/keryx_skill.py

# delivery_mode stays locked in domain/storage/server code and tests.
rg -n 'delivery_mode|agent_only|user_direct' \
  src/maia/keryx_models.py \
  src/maia/keryx_storage.py \
  src/maia/keryx_server.py \
  tests/test_keryx_models.py \
  tests/test_keryx_storage.py \
  tests/test_keryx_server.py
```

## Help checks

```bash
python3 -m maia --help | rg -n \
  'Keryx collaboration contract:|Direct-agent delegation contract:|maia thread show <thread_id>|maia handoff show <handoff_id>'

python3 -m maia thread --help | rg -n \
  'Inspect Keryx-backed collaboration threads|public name for this Keryx collaboration object|distinct from a Hermes session|maia thread list --status open'
```

## Test checks

```bash
python3 -m pytest -q tests/test_cli.py
python3 -m pytest -q tests/test_keryx_models.py tests/test_keryx_storage.py tests/test_keryx_server.py
```
