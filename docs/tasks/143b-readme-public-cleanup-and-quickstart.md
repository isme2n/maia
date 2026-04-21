# Task 143B — README public cleanup + install/quickstart/concepts

## Goal
README를 공개 저장소 첫인상 중심으로 재구성하고, 설치/빠른 시작/핵심 개념을 짧고 분명하게 정리한다.

## Roadmap position
- Execution task for Part 5.

## Non-goals
- CLI 동작/명령 계약 변경
- 테스트 로직 변경

## Allowed files
- `docs/tasks/143b-readme-public-cleanup-and-quickstart.md`
- `README.md`

## Required changes
1) README 상단을 다음 순서로 정리:
   - 제품 정의(짧게)
   - 설치
   - Quickstart(Part 1 bootstrap)
   - 핵심 개념(Maia control plane / Keryx collaboration plane)
2) README의 내부 운영 기록/과도한 상세 레지스트리 나열은 contributor 문서로 이동 가능한 형태로 축약
3) 보조 surface(Portable state, Keryx visibility)는 유지하되 primary bootstrap과 섞이지 않게 분리
4) 새로 분리될 contributor 문서(CONTRIBUTING/TESTING/ARCHITECTURE) 링크 섹션 추가

## Acceptance criteria
- README 첫 스크린에서 사용자 onboarding 흐름이 보인다.
- 설치/빠른 시작/개념 설명이 장황하지 않고 실행 가능하다.
- 내부 구현 세부사항을 public primary section에서 과도하게 노출하지 않는다.

## Validation
- `python3 -m maia --help`
- `python3 -m maia doctor --help`
- `python3 -m pytest -q tests/test_cli.py`
