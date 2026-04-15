# Task 057 - phase4 doctor and infra bootstrap

## Goal
Phase 4에 필요한 로컬 인프라(Docker CLI/Engine, Compose)를 점검하는 `doctor` surface를 추가하고, 현재 머신의 host readiness를 명확히 확인한다.

## Non-goals
- broker 설치
- runtime adapter 구현 전체 완료

## Allowed files
- `src/maia/cli_parser.py`
- `src/maia/cli.py`
- `tests/test_cli.py`
- `tests/test_cli_runtime.py`
- 필요 시 doctor 출력 검증용 테스트 파일

## Acceptance criteria
- [ ] `maia doctor`가 phase4 관련 체크를 출력한다.
- [ ] 최소 체크 항목: docker binary, docker compose, docker daemon reachability.
- [ ] Docker가 없는 host에서도 missing/fail 상태를 명확히 보고한다.
- [ ] fake docker 기반 테스트로 green path를 검증한다.
- [ ] 실제 host 설치가 불가능한 경우에도 Phase 4 다음 작업의 선행 진단 역할을 한다.

## Required validation commands
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
- `PYTHONPATH=src python3 -m maia doctor`

## Forbidden changes
- runtime implementation과 무관한 광범위 리팩터링
