# Keryx Public Contract Matrix

This matrix is the Phase 1 source of truth for active collaboration wording.

- `active`: must remain true in active public/test/code surfaces.
- `removed`: must stay out of active public contract. Negative legacy-only wording is allowed only where noted.
- `legacy-history`: may exist to explain API/history, but is not a public entrypoint.

| command/term | status | canonical wording | README | help | tests | code |
| --- | --- | --- | --- | --- | --- | --- |
| `/keryx` | `active` | User-facing collaboration instruction is `/keryx <instruction>`. | `README.md` Part 2 Keryx collaboration section | top-level help epilog and `thread --help` in `src/maia/cli_parser.py` | `tests/test_cli.py::test_readme_locks_part1_public_flow`; `tests/test_cli.py::test_top_level_help`; `tests/test_cli.py::test_thread_help_includes_examples` | `src/maia/cli_parser.py`; `src/maia/keryx_skill.py` |
| `/call` | `removed` | Do not present `/call` as a current collaboration command. Explicit negative wording that says it is removed is allowed. | may appear only as explicit negative wording that it is removed | may appear only as explicit negative wording that it is removed | tests must lock removal wording and prevent active `/call` command examples | `src/maia/keryx_skill.py` / `src/maia/cli_parser.py` may mention `/call` only to say it is removed/not recommended |
| `/agent-call` | `removed` | Do not present `/agent-call` as a current collaboration command. Explicit negative wording that says it is removed is allowed. | may appear only as explicit negative wording that it is removed | may appear only as explicit negative wording that it is removed | tests must lock removal wording and prevent active `/agent-call` command examples | `src/maia/cli_parser.py` may mention `/agent-call` only to say it is removed |
| `session` / `session_id` | `legacy-history` | Keryx HTTP and Hermes internals may still use `session` / `session_id`, but Maia public collaboration naming is `thread` / `thread_id`. | `README.md` Part 2 Keryx collaboration section | top-level help epilog and `thread --help` in `src/maia/cli_parser.py` | `tests/test_cli.py::test_readme_locks_part1_public_flow`; `tests/test_cli.py::test_thread_help_includes_examples` | `src/maia/cli_parser.py`; `src/maia/keryx_skill.py` HTTP endpoint examples |
| `delivery_mode` | `active` | Keryx message delivery intent uses `delivery_mode` with values `agent_only` and `user_direct`; `user_direct` delivery failure is explicit `failed`; default is `agent_only`. | `README.md` Part 2 Keryx collaboration section | top-level help epilog and `thread --help` in `src/maia/cli_parser.py` | `tests/test_cli.py`; `tests/test_keryx_models.py`; `tests/test_keryx_storage.py`; `tests/test_keryx_server.py` | `src/maia/cli_parser.py`; `src/maia/keryx_models.py`; `src/maia/keryx_storage.py`; `src/maia/keryx_server.py` |

## Notes

- `/keryx` is the active explicit instruction contract and is intentionally repeated in README/help/tests plus the embedded Keryx skill.
- `/call` and `/agent-call` are not active public commands. Explicit negative wording that they are removed is allowed; any positive command usage example is drift.
- `delivery_mode` is an active contract across README/help/tests and model/storage/server code.
