# Task 002 - Agent domain model

## Goal
- Maia가 사용할 최소 agent 도메인 모델을 만든다.
- 아직 DB나 Docker 연동 없이, 상태/정체성/설정의 기본 구조만 코드로 고정한다.

## Non-goals
- 실제 agent 실행
- 파일 저장
- DB 연동
- Docker/Compose 연동
- queue/message 처리

## Allowed files
- `src/maia/agent_model.py`
- `tests/test_agent_model.py`
- `README.md`

## Acceptance criteria
- [ ] `AgentStatus` enum이 있다.
- [ ] 상태는 최소 `running`, `stopped`, `archived`를 가진다.
- [ ] `AgentRecord` dataclass가 있다.
- [ ] `AgentRecord`는 최소 아래 필드를 가진다:
  - `agent_id`
  - `name`
  - `status`
  - `persona`
- [ ] `AgentRecord`를 dict로 직렬화하는 메서드가 있다.
- [ ] dict에서 다시 복원하는 메서드가 있다.
- [ ] 잘못된 status 문자열을 복원하려 하면 명확한 예외를 낸다.
- [ ] 테스트가 최소 4개 있다:
  - enum 값 확인
  - dataclass 생성
  - round-trip serialize/deserialize
  - invalid status error

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`

## Forbidden changes
- CLI 명령 변경
- Docker/DB 관련 코드 추가
- 저장소 쓰기 로직 추가
- memory 시스템 추가

## Implementation notes
- Python 표준 라이브러리만 사용
- dataclass + enum 조합 우선
- persona는 현재 문자열 필드 하나로 단순 유지
- 이후 registry/DB가 붙기 쉬운 형태로 작성

## Suggested shape
- `AgentStatus(str, Enum)`
- `AgentRecord(dataclass)`
- `to_dict()`
- `from_dict()`
