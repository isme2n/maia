"""Keryx collaboration skill content and agent-scoped installation helpers."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from textwrap import dedent

from maia.app_state import get_agent_hermes_home

__all__ = [
    "KERYX_SKILL_CATEGORY",
    "KERYX_SKILL_NAME",
    "KERYX_SKILL_RELATIVE_PATH",
    "ensure_agent_keryx_skill_installed",
    "ensure_keryx_skill_installed",
    "get_agent_keryx_skill_path",
    "render_keryx_skill_content",
]

KERYX_SKILL_NAME = "keryx"
KERYX_SKILL_CATEGORY = "maia"
KERYX_SKILL_RELATIVE_PATH = Path("skills") / KERYX_SKILL_CATEGORY / KERYX_SKILL_NAME / "SKILL.md"


def render_keryx_skill_content() -> str:
    """Return the embedded `/keryx` skill definition shipped with Maia agents."""

    return (
        dedent(
            """
            ---
            name: keryx
            description: 사용자-facing `/keryx <instruction>` 협업 진입점. 자유문 협업 지시를 실제 Keryx HTTP API thread/message/handoff 작업으로 실행한다.
            version: 1.0.0
            author: Maia
            license: MIT
            metadata:
              hermes:
                tags: [maia, keryx, collaboration, slash-command]
            ---

            # keryx

            `/keryx`는 Maia의 명시적 협업 명령이다.
            사용자는 자연어처럼 자유롭게 쓰되, 협업 의도만 명시하면 된다.

            예시:
            - `/keryx 경제에게 지난번 조사했던 거 있으면 그거 좀 달라 그래`
            - `/keryx 테크한테 이 에러 로그 보여주고 원인 먼저 물어봐`
            - `/keryx 경제랑 테크 둘 다 의견 받아서 결론만 정리해줘`

            ## 핵심 규칙

            1. `/keryx` 뒤의 자유문을 명시적 협업 지시로 취급한다.
            2. 사용자에게 `ask`, `reply`, `status` 같은 하위 문법을 다시 요구하지 않는다.
            3. 공개 UX는 항상 자연어 본문만 받는 `/keryx <instruction>` 형식이다. `/call`을 공개 표면으로 되살리거나 추천하지 않는다.
            4. 최종 결과는 항상 현재 사용자-facing 에이전트가 가져와서 정리해 전달한다.

            ## 절대적인 비환각 규칙

            - 실제로 Keryx 리소스를 만들거나 읽지 않았고, 실제 응답 payload를 관찰하지 않았다면 "전달했다", "답을 받았다", "handoff했다", "thread를 찾았다"고 주장하지 않는다.
            - Keryx HTTP API 호출을 실제 도구 실행으로 수행할 수 없으면, 협업을 수행한 척하지 말고 왜 지금 실행하지 못하는지 솔직히 말한다.
            - 성공 보고는 실제 `thread_id/session_id`, 실제 message/handoff 상태, 또는 실제 응답 본문을 확인한 뒤에만 한다.

            ## 실행 모드: 실제 Keryx HTTP API를 사용한다

            런타임이 shell/python/http 도구를 제공하면 설명으로 끝내지 말고 실제 호출을 실행한다.
            `curl`, Python `requests`, 또는 동등한 HTTP 클라이언트를 써도 되지만, 아래 API 흐름을 실제로 수행하고 응답을 확인해야 한다.

            기본 엔드포인트:
            - `GET /agents`
            - `GET /sessions`
            - `POST /sessions`
            - `GET /sessions/{session_id}/messages`
            - `POST /sessions/{session_id}/messages`
            - `GET /sessions/{session_id}/handoffs`
            - `POST /sessions/{session_id}/handoffs`

            ## 최소 실행 워크플로

            1. 현재 자신과 대상 agent를 `GET /agents`로 해석한다.
               - 현재 agent는 roster에서 자신의 agent_id/name과 맞는 항목으로 찾는다.
               - 대상 agent도 사용자의 자연어 지시와 roster를 대조해서 찾는다.
               - 후보가 여럿이면 짧게 확인하되, 확인 전에는 임의 agent에게 보냈다고 말하지 않는다.

            2. session(thread) 선택 규칙을 적용한다.
               - 기본값은 새 session 생성이다.
               - 오직 최근 thread가 분명히 같은 작업/같은 상대/같은 맥락으로 이어지는 것이 명확할 때만 재사용한다.
               - 재사용 검토가 필요하면 `GET /sessions`로 최근 session을 확인한다.

            3. 필요하면 `POST /sessions`로 새 session을 만든다.
               - topic은 사용자의 협업 의도를 짧게 요약한다.
               - participants에는 최소한 현재 agent와 대상 agent를 포함한다.
               - 생성 응답에서 실제 `session_id`를 확인하고 기록한다.
               - 사용자에게는 Maia public 용어로 `thread_id=<session_id>`라고 보고해도 된다.

            4. `POST /sessions/{session_id}/messages`로 요청 메시지를 남긴다.
               - kind는 보통 `request` 또는 `question`을 사용한다.
               - body에는 사용자의 `/keryx` 자유문을 실행 가능한 협업 요청으로 정리해 넣는다.
               - from_agent/to_agent를 실제 roster 해석 결과에 맞춰 채운다.

            5. 정말 필요할 때만 handoff를 만든다.
               - 단순 질문/응답이면 handoff 없이 message만으로 진행한다.
               - 실제 작업 위임, 산출물 위치 전달, 책임 전환이 필요할 때만 `POST /sessions/{session_id}/handoffs`를 사용한다.
               - handoff를 만들지 않았다면 만든 척 말하지 않는다.

            6. 실제 답변이 올 때까지 poll한다.
               - `GET /sessions/{session_id}/messages`를 반복 조회해 대상 agent의 새 `answer`/`report`/관련 응답 message를 찾는다.
               - 자신이 방금 보낸 요청만 보고 완료라고 판단하지 않는다.
               - 합리적인 timeout까지도 답이 없으면 아직 답을 못 받았다고 사실대로 보고한다.

            7. 사용자에게 grounded 결과를 보고한다.
               - 확인한 `thread_id`를 함께 준다.
               - 실제 응답 내용을 요약하되, 관찰한 범위를 넘겨 추론하지 않는다.
               - 실패/대기 중이면 어떤 API 단계까지 실제로 완료했는지 분명히 적는다.

            ## 간단한 실행 예시

            사용자가 `/keryx 테크한테 이 에러 로그 보여주고 원인 먼저 물어봐`라고 하면:
            - `GET /agents`로 self/테크 agent를 찾는다.
            - 분명한 기존 thread가 없으면 `POST /sessions`로 새 session을 만든다.
            - `POST /sessions/{session_id}/messages`로 질문을 보낸다.
            - 필요할 때만 `POST /sessions/{session_id}/handoffs`를 추가한다.
            - `GET /sessions/{session_id}/messages`를 poll해서 테크 agent의 실제 `answer` 또는 `report`를 기다린다.
            - 실제 응답이 오면 `thread_id`와 함께 사용자에게 요약한다.

            ## 애매할 때 fallback

            - 대상 agent가 불명확하면 누구에게 보낼지 한 문장으로 확인한다.
            - "그거", "지난번"처럼 참조가 모호하면 가장 최근 관련 thread를 우선 보되, 확신이 없으면 짧게 확인한다.
            - 여러 agent가 후보면 사용자가 말한 순서와 문맥상 가장 자연스러운 대상을 우선한다.

            ## 금지

            - 사용자를 legacy `/call` 류 문법으로 돌려보내지 않는다.
            - 사용자가 명시적으로 `/keryx`로 협업을 지시했는데 단순 자동 추론 문제로 무시하지 않는다.
            - thread/handoff 내부 용어를 사용자에게 불필요하게 강요하지 않는다.
            - 실제 HTTP 호출/응답 확인 없이 다른 agent가 이미 답했다고 꾸며내지 않는다.
            """
        ).strip()
        + "\n"
    )


def ensure_keryx_skill_installed(hermes_home: Path | str) -> Path:
    """Install or refresh the built-in Keryx skill inside one Hermes home."""

    home = Path(hermes_home)
    skill_path = home / KERYX_SKILL_RELATIVE_PATH
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    content = render_keryx_skill_content()
    if not skill_path.exists() or skill_path.read_text(encoding="utf-8") != content:
        skill_path.write_text(content, encoding="utf-8")
    return skill_path


def ensure_agent_keryx_skill_installed(
    agent_id: str,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Install the built-in Keryx skill into an agent-scoped Hermes home."""

    return ensure_keryx_skill_installed(get_agent_hermes_home(agent_id, env))


def get_agent_keryx_skill_path(
    agent_id: str,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Return the expected built-in Keryx skill path for one agent."""

    return get_agent_hermes_home(agent_id, env) / KERYX_SKILL_RELATIVE_PATH
