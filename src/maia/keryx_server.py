"""Minimal stdlib HTTP server for Keryx Phase 1 resources."""

from __future__ import annotations

import json
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from maia.keryx_models import (
    KeryxHandoffRecord,
    KeryxMessageRecord,
    KeryxSessionRecord,
)
from maia.keryx_service import KeryxResourceNotFoundError, KeryxService

__all__ = [
    "KeryxHttpServer",
    "KeryxRequestHandler",
    "create_keryx_http_server",
]


class _KeryxHttpError(Exception):
    """Internal exception for controlled HTTP error responses."""

    def __init__(
        self,
        *,
        status: HTTPStatus,
        payload: dict[str, Any],
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(payload.get("error", "HTTP error"))
        self.status = status
        self.payload = payload
        self.headers = dict(headers or {})


class KeryxHttpServer(ThreadingHTTPServer):
    """HTTP server that exposes Keryx service operations as JSON routes."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        service: KeryxService | None = None,
        state_db_path: Path | str | None = None,
    ) -> None:
        self.service = (
            KeryxService(state_db_path=state_db_path)
            if service is None
            else service
        )
        super().__init__(server_address, KeryxRequestHandler)


class KeryxRequestHandler(BaseHTTPRequestHandler):
    """Translate HTTP requests into Keryx service operations."""

    server: KeryxHttpServer

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PATCH(self) -> None:  # noqa: N802
        self._dispatch("PATCH")

    def log_message(self, format: str, *args: object) -> None:
        """Suppress default stderr access logs."""

    def _dispatch(self, method: str) -> None:
        path = tuple(segment for segment in urlparse(self.path).path.split("/") if segment)
        try:
            response_status, payload = self._route_request(method, path)
        except _KeryxHttpError as exc:
            self._send_json(exc.status, exc.payload, headers=exc.headers)
            return
        except KeryxResourceNotFoundError as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            return
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._send_json(response_status, payload)

    def _route_request(
        self,
        method: str,
        path: tuple[str, ...],
    ) -> tuple[HTTPStatus, Any]:
        service = self.server.service

        if path == ("agents",):
            if method != "GET":
                self._raise_method_not_allowed(("GET",))
            return HTTPStatus.OK, self._serialize(service.list_roster())

        if len(path) == 3 and path[0] == "agents" and path[2] == "pending-work":
            if method != "GET":
                self._raise_method_not_allowed(("GET",))
            return HTTPStatus.OK, self._serialize(service.list_pending_work(path[1]))

        if path == ("sessions",):
            if method == "GET":
                return HTTPStatus.OK, self._serialize(service.list_sessions())
            if method == "POST":
                record = KeryxSessionRecord.from_dict(self._read_json_object())
                return HTTPStatus.CREATED, self._serialize(service.create_session(record))
            self._raise_method_not_allowed(("GET", "POST"))

        if len(path) == 2 and path[0] == "sessions":
            session_id = path[1]
            if method == "GET":
                return HTTPStatus.OK, self._serialize(service.get_session(session_id))
            if method == "PATCH":
                record = KeryxSessionRecord.from_dict(self._read_json_object())
                return HTTPStatus.OK, self._serialize(
                    service.update_session(session_id, record)
                )
            self._raise_method_not_allowed(("GET", "PATCH"))

        if len(path) == 3 and path[0] == "sessions" and path[2] == "messages":
            session_id = path[1]
            if method == "GET":
                return HTTPStatus.OK, self._serialize(
                    service.list_session_messages(session_id)
                )
            if method == "POST":
                record = KeryxMessageRecord.from_dict(self._read_json_object())
                return HTTPStatus.CREATED, self._serialize(
                    service.create_session_message(session_id, record)
                )
            self._raise_method_not_allowed(("GET", "POST"))

        if len(path) == 3 and path[0] == "sessions" and path[2] == "handoffs":
            session_id = path[1]
            if method == "GET":
                return HTTPStatus.OK, self._serialize(
                    service.list_session_handoffs(session_id)
                )
            if method == "POST":
                record = KeryxHandoffRecord.from_dict(self._read_json_object())
                return HTTPStatus.CREATED, self._serialize(
                    service.create_session_handoff(session_id, record)
                )
            self._raise_method_not_allowed(("GET", "POST"))

        if len(path) == 2 and path[0] == "handoffs":
            handoff_id = path[1]
            if method == "GET":
                return HTTPStatus.OK, self._serialize(service.get_handoff(handoff_id))
            if method == "PATCH":
                record = KeryxHandoffRecord.from_dict(self._read_json_object())
                return HTTPStatus.OK, self._serialize(
                    service.update_handoff(handoff_id, record)
                )
            self._raise_method_not_allowed(("GET", "PATCH"))

        raise KeryxResourceNotFoundError("Route not found")

    def _read_json_object(self) -> dict[str, Any]:
        content_length_text = self.headers.get("Content-Length")
        if content_length_text is None:
            raise ValueError("Request body must be a JSON object")
        try:
            content_length = int(content_length_text)
        except ValueError as exc:
            raise ValueError("Invalid Content-Length header") from exc
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise ValueError("Request body is not valid UTF-8") from exc
        except json.JSONDecodeError as exc:
            raise ValueError("Request body is not valid JSON") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("Request body must be a JSON object")
        return dict(payload)

    def _serialize(self, payload: Any) -> Any:
        if isinstance(payload, list):
            return [self._serialize(item) for item in payload]
        if hasattr(payload, "to_dict"):
            return payload.to_dict()
        return payload

    def _raise_method_not_allowed(self, allowed_methods: tuple[str, ...]) -> None:
        raise _KeryxHttpError(
            status=HTTPStatus.METHOD_NOT_ALLOWED,
            payload={"error": "Method not allowed"},
            headers={"Allow": ", ".join(allowed_methods)},
        )

    def _send_json(
        self,
        status: HTTPStatus,
        payload: Any,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        for header_name, header_value in dict(headers or {}).items():
            self.send_header(header_name, header_value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_keryx_http_server(
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    service: KeryxService | None = None,
    state_db_path: Path | str | None = None,
) -> KeryxHttpServer:
    """Build a Keryx HTTP server bound to the requested address."""

    return KeryxHttpServer(
        (host, port),
        service=service,
        state_db_path=state_db_path,
    )
