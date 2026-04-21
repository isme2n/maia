# Task 143A — Part 5 OSS public surface contract matrix + drift checks

## Goal
Part 5에서 공개 저장소 관점의 public surface를 명시적으로 고정하고 drift-check 기준을 만든다.

## Roadmap position
- Execution task for Part 5.

## Non-goals
- README 본문 대규모 개편(143B에서 처리)
- contributor docs 신설(143C에서 처리)
- 런타임 동작 변경

## Allowed files
- `docs/tasks/143a-public-surface-contract-matrix-and-drift-check.md`
- `docs/contracts/part5-oss-public-surface-matrix.md`
- `docs/contracts/part5-oss-drift-checks.md`

## Required outputs
1) public surface contract matrix:
   - surface
   - audience (`user`, `contributor`, `internal`)
   - status (`primary`, `secondary`, `internal-only`)
   - canonical wording
   - assertion locations
2) drift-check doc:
   - README first section checks(install/quickstart/concepts)
   - contributor-doc split checks(CONTRIBUTING/TESTING/ARCHITECTURE)
   - top-level help sanity checks
   - focused pytest check

## Acceptance criteria
- Part 1 bootstrap와 Part 2 Keryx contract를 유지하면서 OSS public reading order를 명확히 정의한다.
- internal/dev-only narrative(작업 이력/하네스 상세)가 README primary surface에서 분리되어야 한다는 규칙이 명시된다.
- drift-check 명령이 실행 가능하고 과도한 exact-match에 의존하지 않는다.

## Validation
- `python3 -m pytest -q tests/test_cli.py`

## Forbidden changes
- src 코드/테스트 수정 금지
