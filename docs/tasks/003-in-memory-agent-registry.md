# Task 003 - In-memory agent registry

## Goal
- AgentRecord를 관리하는 최소 registry 계층을 만든다.
- 아직 파일 저장 없이 메모리 안에서 생성/조회/목록/상태변경만 지원한다.

## Non-goals
- 파일 저장
- DB 연동
- CLI 연결
- Docker/Compose 연동
- queue 처리

## Allowed files
- `src/maia/registry.py`
- `tests/test_registry.py`
- `README.md`

## Acceptance criteria
- [ ] `AgentRegistry` 클래스가 있다.
- [ ] `add(record)`가 있다.
- [ ] `get(agent_id)`가 있다.
- [ ] `list()`가 있다.
- [ ] `set_status(agent_id, status)`가 있다.
- [ ] 같은 `agent_id`를 두 번 추가하면 명확한 예외를 낸다.
- [ ] 없는 `agent_id`를 조회하거나 상태변경하면 명확한 예외를 낸다.
- [ ] `list()`는 추가 순서를 유지한다.
- [ ] 테스트가 최소 5개 있다:
  - add/get
  - duplicate add error
  - list order
  - set_status success
  - missing id error

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`

## Forbidden changes
- 파일 저장 구현
- DB 코드 추가
- CLI 명령 변경
- Docker/queue 관련 코드 추가

## Implementation notes
- Python 표준 라이브러리만 사용
- 내부 저장은 dict + list 또는 ordered dict 계열로 단순하게
- `AgentRecord`는 불변으로 가정하지 말고, status 변경은 새 record 생성 또는 안전한 방식으로 처리
- 예외 메시지는 테스트 가능할 정도로 명확하게 유지
