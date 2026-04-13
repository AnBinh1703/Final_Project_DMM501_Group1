from __future__ import annotations

import asyncio
import json as jsonlib
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ASGIResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return jsonlib.loads(self.body.decode("utf-8"))


class LifespanManager:
    def __init__(self, app: Any):
        self._app = app
        self._recv_q: asyncio.Queue[dict[str, Any]] | None = None
        self._send_q: asyncio.Queue[dict[str, Any]] | None = None
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> "LifespanManager":
        self._recv_q = asyncio.Queue()
        self._send_q = asyncio.Queue()

        async def receive() -> dict[str, Any]:
            assert self._recv_q is not None
            return await self._recv_q.get()

        async def send(message: dict[str, Any]) -> None:
            assert self._send_q is not None
            await self._send_q.put(message)

        async def run_lifespan() -> None:
            scope = {"type": "lifespan", "state": {}}
            await self._app(scope, receive, send)

        self._task = asyncio.create_task(run_lifespan())
        await self._recv_q.put({"type": "lifespan.startup"})
        msg = await self._send_q.get()
        if msg.get("type") != "lifespan.startup.complete":
            raise RuntimeError(f"Unexpected lifespan startup message: {msg}")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        assert self._recv_q is not None
        assert self._send_q is not None
        assert self._task is not None

        await self._recv_q.put({"type": "lifespan.shutdown"})
        msg = await self._send_q.get()
        if msg.get("type") != "lifespan.shutdown.complete":
            raise RuntimeError(f"Unexpected lifespan shutdown message: {msg}")
        await self._task


def _headers_to_scope(headers: dict[str, str] | None) -> list[tuple[bytes, bytes]]:
    if not headers:
        return []
    return [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]


async def asgi_request(
    app: Any,
    *,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> ASGIResponse:
    parts = urlsplit(url)
    path = parts.path or "/"
    query_string = (parts.query or "").encode("ascii")

    received_any = False
    response_status: int | None = None
    response_headers: list[tuple[bytes, bytes]] = []
    response_body_parts: list[bytes] = []

    scope = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii", errors="ignore"),
        "query_string": query_string,
        "headers": _headers_to_scope(headers),
        "client": ("testclient", 12345),
        "server": ("testserver", 80),
        "state": {},
    }

    async def receive() -> dict[str, Any]:
        nonlocal received_any
        if not received_any:
            received_any = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        nonlocal response_status, response_headers
        msg_type = message.get("type")
        if msg_type == "http.response.start":
            response_status = int(message["status"])
            response_headers = list(message.get("headers") or [])
        elif msg_type == "http.response.body":
            response_body_parts.append(message.get("body", b""))
        else:
            raise RuntimeError(f"Unexpected ASGI message type: {msg_type}")

    await app(scope, receive, send)

    if response_status is None:
        raise RuntimeError("No response received from ASGI app")

    headers_out: dict[str, str] = {}
    for k, v in response_headers:
        headers_out[k.decode("latin-1")] = v.decode("latin-1")

    return ASGIResponse(status_code=response_status, headers=headers_out, body=b"".join(response_body_parts))


async def asgi_get_json(app: Any, url: str) -> Any:
    resp = await asgi_request(app, method="GET", url=url)
    return resp.json()


async def asgi_post_json(app: Any, url: str, payload: dict[str, Any]) -> ASGIResponse:
    body = jsonlib.dumps(payload).encode("utf-8")
    headers = {"content-type": "application/json"}
    return await asgi_request(app, method="POST", url=url, headers=headers, body=body)

