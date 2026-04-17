# Task 125 — bootstrap UX hardening and gateway readiness

## Goal
- Part 1 bootstrap flow를 일반 사용자 기준으로 더 정직하고 자연스럽게 만든다.
- `maia agent new`는 이름/사용자 호칭(call-sign)/persona를 즉시 묻는 interactive creation flow로 고정한다.
- gateway를 놓쳤을 때 Maia 안에서 복구할 수 있는 backup command를 제공하고, gateway readiness가 없으면 `agent start`를 막는다.
- `doctor`와 `setup` 출력은 machine-ish field dump보다 짧고 강조된 operator-facing summary를 기본값으로 제공한다.

## Non-goals
- host package auto-install
- latest-version-only enforcement
- dashboard/UI work
- unrelated Part 3+ roadmap work

## Allowed files
- `README.md`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `src/maia/agent_setup_session.py`
- `src/maia/docker_runtime_adapter.py`
- `src/maia/runtime_adapter.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `docs/tasks/125-bootstrap-ux-hardening-and-gateway-readiness.md`

## Acceptance criteria
- [x] `maia agent new` without flags/positionals immediately prompts for agent name, how the agent addresses the user (`call_sign`), and persona.
- [x] successful `agent new` stores those three identity values and prints the next step: `maia agent setup <name>`.
- [x] `maia agent setup-gateway <name>` exists and reruns `hermes setup gateway` inside the agent-scoped Hermes home.
- [x] `maia agent start <name>` fails clearly when gateway readiness is incomplete.
- [x] the gateway readiness failure tells the operator to run `maia agent setup-gateway <name>`.
- [x] `doctor` default output is short operator-facing summary text rather than `doctor check=...` field lines.
- [x] `setup` output keeps the shared infra summary concise and points to `maia agent new` as the next step.
- [x] README/help/tests align to the same new bootstrap story.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `cd /home/asle/maia && bash scripts/verify.sh`

## Forbidden changes
- adding persona/call-sign as required command-line flags instead of interactive prompts
- weakening start gating back to setup-only if gateway remains missing
- broad cleanup outside the allowed files

## Design notes
- `call_sign` in current Maia plans already means the user nickname/how the agent addresses the user; use that existing field instead of inventing a second identity field here.
- `doctor` should remain infra-only and should not silently mutate the host.
- gateway readiness should be checked from the agent-scoped Hermes home/config outcome, not from repo-global user assumptions.
- keep backward compatibility only where it does not weaken the new public contract.
