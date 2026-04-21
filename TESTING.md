# Testing Maia

Run commands from the repository root.

## Core commands

Fast:

```bash
python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py
```

Use this when changing README/help text, bootstrap wording, or runtime command behavior.

Focused:

```bash
python3 -m pytest -q tests/test_cli.py -k "<keyword>"
python3 -m pytest -q tests/test_cli_runtime.py -k "<keyword>"
```

Use this while iterating on one CLI or runtime contract slice.

Full:

```bash
bash scripts/verify.sh
```

Use this before handing work to review. `scripts/verify.sh` is the repo-wide validation entry point and currently runs the full pytest suite.

## Default debug loop

1. Reproduce the failure with the smallest failing command.
2. Narrow it to one file or one `-k` filter.
3. Check the locked contract surface that the test is exercising.
4. Apply the smallest fix that resolves that contract break.
5. Rerun the exact failing test, then the task-level command, then the full verify command.

Typical contract surfaces:
- README/help wording mismatches: `README.md`, `src/maia/cli_parser.py`, `tests/test_cli.py`
- runtime command behavior mismatches: `src/maia/cli.py`, `src/maia/runtime_*`, `tests/test_cli_runtime.py`
- Keryx collaboration state mismatches: `src/maia/keryx_*`, related model/storage tests

## Runtime test boundary

- Fake-docker tests validate Maia's runtime command flow, not whether Docker works on the current host.
- If a live runtime command fails outside pytest, run `maia doctor` first and treat host readiness separately from the unit-test result.
