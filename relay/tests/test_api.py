"""API endpoint tests using FastAPI's TestClient.

Mocks the bridge module entirely so no pyrogram/pytgcalls is needed.
"""
import os
import sys
import types
from unittest.mock import AsyncMock

import pytest

# Set test env vars before any app imports
os.environ.setdefault("TELEGRAM_APP_ID", "12345")
os.environ.setdefault("TELEGRAM_APP_HASH", "testhash")
os.environ.setdefault("TELEGRAM_PHONE", "+1234567890")

# Stub out bridge module before main.py imports it
_bridge_mod = types.ModuleType("bridge")


class _FakeCallBridge:
    def __init__(self, **kw):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def join(self, session):
        pass


_bridge_mod.CallBridge = _FakeCallBridge  # type: ignore[attr-defined]
sys.modules["bridge"] = _bridge_mod

from fastapi.testclient import TestClient  # noqa: E402

from main import app, mgr  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_sessions():
    mgr._sessions.clear()
    yield
    mgr._sessions.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_session_start(client):
    resp = client.post("/session/start", json={"chat_id": 123})
    assert resp.status_code == 201
    body = resp.json()
    assert "session_id" in body
    assert "/audio/" in body["audio_url"]


def test_session_start_missing_chat_id(client):
    resp = client.post("/session/start", json={})
    assert resp.status_code == 422


def test_session_end(client):
    resp = client.post("/session/start", json={"chat_id": 456})
    sid = resp.json()["session_id"]
    resp = client.post("/session/end", json={"session_id": sid})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ended"


def test_session_end_not_found(client):
    resp = client.post("/session/end", json={"session_id": "bad"})
    assert resp.status_code == 404


def test_session_list(client):
    client.post("/session/start", json={"chat_id": 10})
    client.post("/session/start", json={"chat_id": 20})
    resp = client.get("/sessions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_session_list_empty(client):
    resp = client.get("/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_duplicate_chat_returns_409(client):
    client.post("/session/start", json={"chat_id": 77})
    resp = client.post("/session/start", json={"chat_id": 77})
    assert resp.status_code == 409
