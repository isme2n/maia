# Portable-State Drift Checks

Run from the repo root. The help checks below use the module-entrypoint form (`python3 -m maia`). If the current interpreter does not resolve `maia`, rerun in an environment where Maia is installed or importable (for example `PYTHONPATH=src`).

## Text checks

```bash
# export/import primary surface exists
rg -n 'maia export' README.md src/maia/cli_parser.py tests/test_cli.py tests/test_cli_runtime.py
rg -n 'maia import <path>' README.md src/maia/cli_parser.py tests/test_cli.py tests/test_cli_runtime.py

# import safety flags are present
rg -n -- '--preview' README.md src/maia/cli_parser.py tests/test_cli.py tests/test_cli_runtime.py
rg -n -- '--yes' README.md src/maia/cli_parser.py tests/test_cli.py tests/test_cli_runtime.py

# destructive-import confirmation behavior is present
rg -n 'asks for confirmation' README.md
rg -n 'overwrite-confirm skip behavior' README.md
rg -n 'confirm prompt=Proceed with overwrite import\? \[y/N\]' tests/test_cli_runtime.py
rg -n 'Proceed with overwrite import\? \[y/N\]' src/maia/cli.py

# inspect support surface is present
rg -n 'maia inspect <path>' README.md tests/test_cli.py
rg -n 'Inspect an importable Maia snapshot' src/maia/cli_parser.py tests/test_cli.py
rg -n 'inspects an importable Maia snapshot' README.md
```

## Help checks

```bash
python3 -m maia --help | rg -n 'Export Maia portable state'
python3 -m maia --help | rg -n 'Import Maia portable state safely'
python3 -m maia --help | rg -n 'Inspect an importable Maia snapshot'

python3 -m maia import --help | rg -n 'Show the import preview and risk summary'
python3 -m maia import --help | rg -n 'Show full added/removed/changed preview lists'
python3 -m maia import --help | rg -n 'Skip overwrite confirmation for destructive imports'
python3 -m maia import --help | rg -n 'maia import backups/team.maia --preview'
python3 -m maia import --help | rg -n 'maia import backups/team.maia --yes'

python3 -m maia export --help | rg -n 'maia export backups/team.maia'
python3 -m maia export --help | rg -n -- '--label'
python3 -m maia export --help | rg -n -- '--description'
python3 -m maia export --help | tr '\n' ' ' | rg -q 'Write a Maia bundle \(.maia\) or raw registry snapshot path'
```

## Test checks

```bash
python3 -m pytest -q tests/test_cli.py

python3 -m pytest -q \
  tests/test_cli.py::test_top_level_help \
  tests/test_cli.py::test_import_help_describes_safety_flags \
  tests/test_cli.py::test_inspect_help_includes_examples \
  tests/test_cli.py::test_export_help_includes_examples \
  tests/test_cli.py::test_readme_examples_align_with_public_help

python3 -m pytest -q \
  tests/test_cli_runtime.py::test_team_show_update_export_and_inspect_scope_v3_bundle \
  tests/test_cli_runtime.py::test_export_and_inspect_encode_paths_and_metadata_with_spaces \
  tests/test_cli_runtime.py::test_import_preview_reports_role_model_tags_diffs_and_imports \
  tests/test_cli_runtime.py::test_import_preview_reports_team_metadata_diffs \
  tests/test_cli_runtime.py::test_import_without_yes_requires_confirmation_for_team_only_changes
```
