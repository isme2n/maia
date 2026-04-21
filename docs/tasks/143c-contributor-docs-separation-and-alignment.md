# Task 143C — Contributor docs separation (CONTRIBUTING / TESTING / ARCHITECTURE)

## Goal
contributor-facing 문서를 user-facing README에서 분리하고, 기여자 온보딩 동선을 고정한다.

## Roadmap position
- Execution task for Part 5.

## Non-goals
- 코드 리팩터링
- CI 파이프라인 신규 도입

## Allowed files
- `docs/tasks/143c-contributor-docs-separation-and-alignment.md`
- `CONTRIBUTING.md`
- `TESTING.md`
- `ARCHITECTURE.md`
- `README.md`

## Required changes
1) `CONTRIBUTING.md` 생성:
   - 개발 환경 준비
   - 하네스 워크플로(worker/verify/reviewer)
   - PR/커밋 규칙
2) `TESTING.md` 생성:
   - 핵심 테스트 명령(빠른/집중/전체)
   - 실패 시 디버깅 기본 루프
3) `ARCHITECTURE.md` 생성:
   - control plane vs collaboration plane 경계
   - 주요 모듈 지도(간결)
4) README에는 contributor entry 링크만 남기고 상세는 분리 문서로 이동

## Acceptance criteria
- 신규 기여자가 README에서 contributor 문서로 바로 이동 가능하다.
- CONTRIBUTING/TESTING/ARCHITECTURE 각 문서의 역할이 겹치지 않는다.
- 하네스 기반 개발 흐름이 문서로 명확히 고정된다.

## Validation
- `python3 -m pytest -q tests/test_cli.py tests/test_cli_runtime.py`
