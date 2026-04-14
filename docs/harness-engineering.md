# Harness Engineering for Maia

## 정의
여기서 harness engineering은 모델 프롬프트 자체보다, 에이전트가 안정적으로 일하도록 둘러싼 실행 프레임을 설계하는 것을 뜻한다.

핵심은 아래 6가지다.
- 작업 계약(task contract)
- 역할 분리(worker / reviewer)
- 자동 검증(test / lint / typecheck)
- 고정된 리뷰 출력 형식
- fix loop 최대 반복 횟수
- 로그와 산출물 보존

## Maia 기본 규칙
- worker와 reviewer는 분리한다.
- planner는 큰 작업이나 애매한 작업에서만 추가한다.
- reviewer는 구현보다 결함 탐지에 집중한다.
- 자동 검증이 reviewer 감정보보다 우선한다.
- 작업은 작게 쪼갠다.
- 변경 허용 경로를 명시한다.

## 참고한 하네스 관점
- OpenAI/Anthropic식 하네스 엔지니어링: 실행 환경, 피드백 루프, 제약, 평가, 복구까지 포함한 상위 개념
- revfactory/harness: 팀 구조와 스킬을 설계하는 design harness 관점이 강함
- oh-my-openagent: 오케스트레이션, 복구, 라우팅, 편집 신뢰성 같은 runtime harness 관점이 강함
- gstack 계열: plan → review → test → ship 같은 workflow harness 관점이 강함

## Maia에 적용할 3층 구조
1. design harness
- agent 역할(planner / worker / reviewer)
- task contract 템플릿
- persona / soul 분리

2. runtime harness
- Codex 프로필(worker / reviewer)
- verify 스크립트
- 장시간 작업 감시, 재시도, 상태 확인
- 이후 Docker / Compose / DB / Queue 추가

3. workflow harness
- spec 작성
- worker 구현
- verify 실행
- reviewer 리뷰
- fix loop
- 승인 후 다음 단계 진행

## Worker 입력 필수 항목
- goal
- non-goals
- allowed files
- acceptance criteria
- required validation commands
- forbidden changes

## Reviewer 입력 필수 항목
- 원래 task spec
- git diff
- 변경 파일 목록
- 검증 결과
- worker 요약

## Reviewer 출력 형식
- reviewer는 최종 응답에 marker block을 반드시 포함한다.
- block 형식:
  - `REVIEW_RESULT_START`
  - `verdict: approve | request_changes`
  - `blocking_issues:`
  - `non_blocking_suggestions:`
  - `touched_risks:`
  - `summary:`
  - `REVIEW_RESULT_END`
- 승인 여부는 watch 문자열이 아니라 이 block을 파싱해서 판정한다.

## Fix loop 규칙
- 최대 3회까지 반복
- 3회 초과 시 작업 재분해 또는 사람 검토로 승격

## 권장 흐름
1. task 작성
2. worker 구현
3. `scripts/verify.sh` 실행
4. reviewer 리뷰
5. issue 있으면 worker 수정
6. 다시 verify
7. 다시 review
