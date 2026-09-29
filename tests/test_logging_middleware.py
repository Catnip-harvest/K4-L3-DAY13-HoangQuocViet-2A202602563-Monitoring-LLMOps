from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import httpx
import structlog

from app import logging_config
from app.main import app

CHAT_BODY = {
    "user_id": "student-01",
    "session_id": "session-01",
    "feature": "qa",
    "message": "My phone is 0987654321 and card 4111 1111 1111 1111",
}


def _post_chat(headers: dict[str, str] | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/chat", json=CHAT_BODY, headers=headers or {})

    return asyncio.run(send())


def _events(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def test_generates_correlation_id_and_response_time_header(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")
    response = _post_chat()

    correlation_id = response.headers["x-request-id"]
    assert re.fullmatch(r"req-[0-9a-f]{8}", correlation_id)
    assert response.json()["correlation_id"] == correlation_id
    assert float(response.headers["x-response-time-ms"]) > 0


def test_reuses_safe_incoming_id_and_rejects_unsafe_one(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")
    assert _post_chat({"x-request-id": "req-client01"}).headers["x-request-id"] == "req-client01"

    unsafe = _post_chat({"x-request-id": 'bad id\n{"level":"error"}'}).headers["x-request-id"]
    assert re.fullmatch(r"req-[0-9a-f]{8}", unsafe)


def test_api_logs_are_enriched_scrubbed_and_do_not_leak_between_requests(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    first = _post_chat().headers["x-request-id"]
    second = _post_chat().headers["x-request-id"]
    assert first != second

    api_events = [e for e in _events(log_path) if e.get("service") == "api"]
    assert {e["correlation_id"] for e in api_events} == {first, second}
    for event in api_events:
        for field in ("user_id_hash", "session_id", "feature", "model", "env"):
            assert event[field], field
        assert event["user_id_hash"] != "student-01"

    raw = log_path.read_text(encoding="utf-8")
    assert "0987654321" not in raw
    assert "4111 1111 1111 1111" not in raw
    assert "REDACTED_PHONE_VN" in raw


def test_scrubber_runs_before_the_file_writer(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    processors = structlog.get_config()["processors"]
    names = [getattr(p, "__name__", type(p).__name__) for p in processors]
    assert names.index("scrub_event") < names.index("JsonlFileProcessor")

    structlog.get_logger().info("manual", service="test", note="mail me at a@b.co")
    assert "a@b.co" not in log_path.read_text(encoding="utf-8")
