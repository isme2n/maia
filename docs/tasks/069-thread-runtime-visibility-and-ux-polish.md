# Task 069 — Runtime-enriched thread visibility and phase7 UX polish

## Goal
- thread visibility에 participant runtime status를 연결하고, help/README를 Phase 7 operator workflow 기준으로 마무리한다.

## Non-goals
- heartbeat daemon
- presence storage redesign
- Docker runtime behavior 변경

## Allowed files
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- `README.md`

## Acceptance criteria
- [ ] `thread list` 또는 `thread show`에서 participant별 runtime status가 보인다.
- [ ] runtime state가 없을 때는 safe default (`stopped`) 또는 명시적 fallback policy가 일관되게 적용된다.
- [ ] collaboration help/examples가 `start -> send/reply -> artifact -> thread list/show -> status` 흐름을 보여준다.
- [ ] thread/artifact output wording이 broker detail을 과하게 노출하지 않는다.
- [ ] targeted tests와 full verify가 통과한다.

## Required validation commands
- `cd /home/asle/maia && PYTHONPATH=src python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `cd /home/asle/maia && bash scripts/verify.sh`

## Forbidden changes
- RabbitMQ adapter semantics
- Docker adapter semantics (unless a blocker is discovered during verify)
- export/import manifests

## Notes
- Phase 7은 control-plane visibility completion이므로 runtime status는 lightweight operator signal로만 붙인다.
- output은 계속 terse key=value lines를 유지한다.
