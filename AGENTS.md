# Maia Codex Harness Rules

이 저장소는 Codex CLI를 작업 에이전트로 사용한다.

## 역할
- worker Codex: 구현 담당
- reviewer Codex: 리뷰 담당
- worker는 자기 작업을 스스로 승인하지 않는다.

## 공통 원칙
- 작은 작업 단위로만 진행한다.
- 작업 전 `docs/tasks/<slug>.md` 같은 명세를 먼저 만든다.
- 요구사항 밖 변경 금지.
- 변경 후 반드시 검증 명령을 실행한다.
- 리뷰 결과의 blocking issue는 반드시 수정 후 재리뷰한다.

## 기본 루프
1. task spec 작성
2. worker Codex가 구현
3. 검증 스크립트 실행
4. reviewer Codex가 diff + spec + 검증 결과 리뷰
5. blocking issue 있으면 worker Codex가 수정
6. 재검증
7. 재리뷰

## 종료 조건
- spec 충족
- 검증 통과
- reviewer 승인

## 금지
- 큰 범위 리팩터링 몰아하기
- spec 없는 구현 시작
- reviewer 승인 없이 완료 처리
- 테스트/검증 생략
