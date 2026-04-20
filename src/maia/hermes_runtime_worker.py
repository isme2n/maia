"""Minimal Keryx-driven Hermes runtime worker for Maia containers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
import subprocess
import sys
import time
from typing import Any, Protocol
from urllib import error, request
import uuid

from maia.keryx_models import (
    KeryxAgentSummary,
    KeryxHandoffRecord,
    KeryxHandoffStatus,
    KeryxMessageRecord,
    KeryxPendingThreadWorkView,
    KeryxPendingWorkRecord,
    KeryxThreadHandoffView,
    KeryxThreadMessageView,
)
from maia.message_model import MessageKind

__all__ = [
    "HttpKeryxClient",
    "WorkerConfig",
    "build_prompt",
    "default_hermes_runner",
    "load_config_from_env",
    "main",
    "process_once",
    "run_forever",
]


@dataclass(slots=True)
class WorkerConfig:
    agent_id: str
    agent_name: str
    keryx_base_url: str = ""
    poll_seconds: float = 2.0
    max_messages_per_poll: int = 1
    hermes_bin: str = "hermes"
    reply_kind: MessageKind = MessageKind.ANSWER


HermesRunner = Callable[[str], str] | Callable[[str, "WorkerConfig"], str]


class KeryxClient(Protocol):
    def list_agents(self) -> list[KeryxAgentSummary]: ...

    def list_pending_work(
        self,
        *,
        agent_id: str,
        limit: int = 1,
    ) -> list[KeryxPendingThreadWorkView]: ...

    def list_thread_messages(self, thread_id: str) -> list[KeryxThreadMessageView]: ...

    def list_thread_handoffs(self, thread_id: str) -> list[KeryxThreadHandoffView]: ...

    def create_thread_message(
        self,
        thread_id: str,
        record: KeryxThreadMessageView,
    ) -> KeryxThreadMessageView: ...

    def update_thread_handoff(
        self,
        handoff_id: str,
        record: KeryxThreadHandoffView,
    ) -> KeryxThreadHandoffView: ...


class HttpKeryxClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def list_agents(self) -> list[KeryxAgentSummary]:
        return [
            KeryxAgentSummary.from_dict(item)
            for item in self._request_json("GET", "/agents")
        ]

    def list_pending_work(
        self,
        *,
        agent_id: str,
        limit: int = 1,
    ) -> list[KeryxPendingThreadWorkView]:
        payload = self._request_json("GET", f"/agents/{agent_id}/pending-work")
        return [
            KeryxPendingThreadWorkView.from_pending_work_record(
                KeryxPendingWorkRecord.from_dict(item)
            )
            for item in payload[:limit]
        ]

    def list_thread_messages(self, thread_id: str) -> list[KeryxThreadMessageView]:
        return [
            KeryxThreadMessageView.from_message_record(KeryxMessageRecord.from_dict(item))
            for item in self._request_json("GET", f"/sessions/{thread_id}/messages")
        ]

    def list_thread_handoffs(self, thread_id: str) -> list[KeryxThreadHandoffView]:
        return [
            KeryxThreadHandoffView.from_handoff_record(KeryxHandoffRecord.from_dict(item))
            for item in self._request_json("GET", f"/sessions/{thread_id}/handoffs")
        ]

    def create_thread_message(
        self,
        thread_id: str,
        record: KeryxThreadMessageView,
    ) -> KeryxThreadMessageView:
        payload = self._request_json(
            "POST",
            f"/sessions/{thread_id}/messages",
            payload=record.to_message_record().to_dict(),
        )
        return KeryxThreadMessageView.from_message_record(
            KeryxMessageRecord.from_dict(payload)
        )

    def update_thread_handoff(
        self,
        handoff_id: str,
        record: KeryxThreadHandoffView,
    ) -> KeryxThreadHandoffView:
        payload = self._request_json(
            "PATCH",
            f"/handoffs/{handoff_id}",
            payload=record.to_handoff_record().to_dict(),
        )
        return KeryxThreadHandoffView.from_handoff_record(
            KeryxHandoffRecord.from_dict(payload)
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        body: bytes | None = None
        headers: dict[str, str] = {}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            response = request.urlopen(
                request.Request(
                    f"{self._base_url}{path}",
                    data=body,
                    headers=headers,
                    method=method,
                )
            )
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip() or exc.reason
            raise ValueError(f"Keryx request failed: {detail}") from exc
        except error.URLError as exc:
            raise ValueError(f"Keryx request failed: {exc.reason}") from exc
        with response:
            return json.loads(response.read().decode("utf-8"))


def load_config_from_env(env: dict[str, str] | None = None) -> WorkerConfig:
    source = os.environ if env is None else env
    agent_id = source.get("MAIA_AGENT_ID", "").strip()
    if not agent_id:
        raise ValueError("MAIA_AGENT_ID is required")
    keryx_base_url = source.get("KERYX_BASE_URL", "").strip()
    if not keryx_base_url:
        raise ValueError("KERYX_BASE_URL is required")
    agent_name = source.get("MAIA_AGENT_NAME", "").strip() or agent_id
    return WorkerConfig(
        agent_id=agent_id,
        agent_name=agent_name,
        keryx_base_url=keryx_base_url.rstrip("/"),
        poll_seconds=float(source.get("MAIA_POLL_SECONDS", "2")),
        max_messages_per_poll=int(source.get("MAIA_MAX_MESSAGES_PER_POLL", "1")),
        hermes_bin=source.get("MAIA_HERMES_BIN", "hermes").strip() or "hermes",
        reply_kind=MessageKind(source.get("MAIA_HERMES_REPLY_KIND", MessageKind.ANSWER.value)),
    )


def build_prompt(
    config: WorkerConfig,
    pending_work: KeryxPendingThreadWorkView,
    *,
    roster: list[KeryxAgentSummary],
    recent_messages: list[KeryxThreadMessageView],
    recent_handoffs: list[KeryxThreadHandoffView],
) -> str:
    message = pending_work.message
    thread = pending_work.thread
    roster_lines = [
        f"  - {entry.name} (agent_id={entry.agent_id}, role={entry.role or '-'}, runtime={entry.runtime_status})"
        for entry in roster
    ] or ["  - -"]
    recent_message_lines = [
        "  - "
        f"message_id={item.message_id} from={item.from_agent} to={item.to_agent} "
        f"kind={item.kind} reply_to={item.reply_to_message_id or '-'} body={item.body}"
        for item in recent_messages[-5:]
    ] or ["  - -"]
    recent_handoff_lines = [
        "  - "
        f"handoff_id={item.handoff_id} type={item.kind} from={item.from_agent} to={item.to_agent} "
        f"status={item.status} summary={item.summary} location={item.location}"
        for item in recent_handoffs[-3:]
    ] or ["  - -"]
    context_block = "\n".join(
        [
            "Current Maia context:",
            "- Known team roster:",
            *roster_lines,
            "- Active thread:",
            f"  - thread_id={thread.thread_id}",
            f"  - topic={thread.topic or '-'}",
            f"  - participants={','.join(thread.participants) if thread.participants else '-'}",
            f"  - status={thread.status}",
            f"  - assigned_handoff={pending_work.handoff.handoff_id}",
            "- Recent thread messages:",
            *recent_message_lines,
            "- Recent handoffs for this thread:",
            *recent_handoff_lines,
        ]
    )
    return (
        f"You are Maia agent {config.agent_name} (agent_id={config.agent_id}).\n\n"
        f"{context_block}\n\n"
        "Reply as this agent to the incoming Maia thread message below.\n"
        "Keep the answer direct and useful. Return only the reply body.\n\n"
        f"thread_id: {message.thread_id}\n"
        f"from_agent: {message.from_agent}\n"
        f"to_agent: {message.to_agent}\n"
        f"message_kind: {message.kind}\n"
        f"message_id: {message.message_id}\n"
        f"message_body:\n{message.body}\n"
    )


def default_hermes_runner(prompt: str, *, config: WorkerConfig) -> str:
    completed = subprocess.run(
        [config.hermes_bin, "chat", "-Q", "-q", prompt],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "hermes command failed").strip()
        raise ValueError(f"Hermes runtime query failed: {detail}")
    reply = completed.stdout.strip()
    if not reply:
        raise ValueError("Hermes runtime query failed: empty response")
    return reply


def process_once(
    config: WorkerConfig,
    *,
    keryx_client: KeryxClient,
    hermes_runner: Callable[..., str] = default_hermes_runner,
) -> bool:
    pending_items = keryx_client.list_pending_work(
        agent_id=config.agent_id,
        limit=config.max_messages_per_poll,
    )
    if not pending_items:
        return False

    processed_any = False
    for pending_work in pending_items:
        try:
            prompt = build_prompt(
                config,
                pending_work,
                roster=keryx_client.list_agents(),
                recent_messages=keryx_client.list_thread_messages(
                    pending_work.thread.thread_id
                ),
                recent_handoffs=keryx_client.list_thread_handoffs(
                    pending_work.thread.thread_id
                ),
            )
            reply_body = hermes_runner(prompt, config=config)
        except Exception as exc:
            print(f"worker agent_id={config.agent_id} status=hermes-error detail={exc}", file=sys.stderr)
            return False
        reply = KeryxThreadMessageView(
            message_id=_new_id(),
            thread_id=pending_work.thread.thread_id,
            from_agent=config.agent_id,
            to_agent=pending_work.message.from_agent,
            kind=config.reply_kind.value,
            body=reply_body,
            created_at=_timestamp_now(),
            reply_to_message_id=pending_work.message.message_id,
        )
        updated_handoff = KeryxThreadHandoffView(
            handoff_id=pending_work.handoff.handoff_id,
            thread_id=pending_work.handoff.thread_id,
            from_agent=pending_work.handoff.from_agent,
            to_agent=pending_work.handoff.to_agent,
            kind=pending_work.handoff.kind,
            status=KeryxHandoffStatus.DONE.value,
            summary=pending_work.handoff.summary,
            location=pending_work.handoff.location,
            created_at=pending_work.handoff.created_at,
            updated_at=reply.created_at,
        )
        keryx_client.create_thread_message(reply.thread_id, reply)
        keryx_client.update_thread_handoff(updated_handoff.handoff_id, updated_handoff)
        processed_any = True
    return processed_any


def run_forever(
    config: WorkerConfig,
    *,
    keryx_client: KeryxClient,
    hermes_runner: Callable[..., str] = default_hermes_runner,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    while True:
        processed = process_once(
            config,
            keryx_client=keryx_client,
            hermes_runner=hermes_runner,
        )
        if not processed:
            sleep_fn(config.poll_seconds)


def main() -> int:
    config = load_config_from_env()
    run_forever(config, keryx_client=HttpKeryxClient(config.keryx_base_url))
    return 0


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _timestamp_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
