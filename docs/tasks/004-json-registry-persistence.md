# Task 004 - JSON registry persistence

## Goal
- Maia agent registry를 JSON 파일로 저장하고 다시 불러오는 최소 persistence 계층을 만든다.
- 아직 CLI 연결이나 ~/.maia 경로 확정은 하지 않고, 파일 입출력 경계만 안전하게 고정한다.

## Non-goals
- CLI 명령 연결
- ~/.maia 전역 경로 결정
- Docker/Compose 연동
- DB/queue 도입
- memory 저장

## Allowed files
- `src/maia/storage.py`
- `tests/test_storage.py`
- `README.md`

## Acceptance criteria
- [ ] `JsonRegistryStorage` 클래스가 있다.
- [ ] 지정된 파일 경로에 registry 내용을 저장하는 메서드가 있다.
- [ ] 지정된 파일 경로에서 registry 내용을 불러오는 메서드가 있다.
- [ ] 저장 형식은 JSON object 하나이며, agent record 배열을 포함한다.
- [ ] 존재하지 않는 파일을 load하면 빈 `AgentRegistry`를 반환한다.
- [ ] 잘못된 JSON 형식이면 명확한 예외를 낸다.
- [ ] load 후 registry의 순서와 상태값이 유지된다.
- [ ] 테스트가 최소 5개 있다:
  - save/load round trip
  - missing file returns empty registry
  - invalid JSON error
  - insertion order preserved
  - archived/running/stopped status preservation

## Required validation commands
- `bash scripts/verify.sh`
- `python3 -m pytest -q`

## Forbidden changes
- CLI 코드 변경
- agent model 변경
- registry API 변경
- Docker/DB/queue 관련 코드 추가

## Implementation notes
- Python 표준 라이브러리만 사용
- JSON 구조는 단순하고 명시적으로 유지
- `pathlib.Path` 사용 우선
- 부모 디렉토리가 없으면 save 시 자동 생성 가능
- 예외 메시지는 테스트 가능할 정도로 명확하게 유지

## Suggested shape
- `class JsonRegistryStorage:`
- `save(path: Path | str, registry: AgentRegistry) -> None`
- `load(path: Path | str) -> AgentRegistry`
