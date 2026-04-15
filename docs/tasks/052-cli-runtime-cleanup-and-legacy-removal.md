# Task 052 - CLI runtime cleanup and legacy removal

## Goal
현재 Maia CLI에서 남아 있는 placeholder/legacy 경로를 제거하고, runtime dispatch 구조를 더 명확하게 정리한다.

## Non-goals
- 새로운 사용자 기능 추가
- broker/runtime adapter 실구현 착수
- command surface 변경

## Allowed files
- `docs/tasks/052-cli-runtime-cleanup-and-legacy-removal.md`
- `src/maia/cli.py`
- `src/maia/cli_parser.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- 필요 시 관련 import 경로를 맞추는 최소 범위 파일

## Acceptance criteria
- [ ] `main(argv)`와 module entrypoint가 같은 runtime semantics를 사용한다.
- [ ] placeholder-only compatibility branch가 제거된다.
- [ ] parser construction과 runtime execution 책임이 분리된다.
- [ ] 기존 command surface(`agent`, `team`, `export/import/inspect`, `send/inbox/thread/reply`)는 유지된다.
- [ ] 관련 테스트가 parser contract와 runtime behavior로 명확히 분리된다.
- [ ] `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py tests/test_collaboration_storage.py tests/test_registry.py tests/test_storage.py`
- [ ] `bash scripts/verify.sh`

## Forbidden changes
- export/import portable-state semantics 변경
- collaboration model 변경
- phase 4 범위 구현 선행

## Notes
- 현재 `src/maia/cli.py`는 parser/placeholder/runtime logic가 함께 섞여 있다.
- Task 001의 placeholder contract는 이제 실제 제품 흐름을 흐리므로 제거한다.
- parser shape 검증은 `build_parser()` 중심 테스트로 유지하고, 실제 동작 검증은 subprocess/runtime 테스트가 담당한다.
