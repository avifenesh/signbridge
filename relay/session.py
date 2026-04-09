from __future__ import annotations

import asyncio
import enum
import time
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket


class State(str, enum.Enum):
    JOINING = "joining"
    ACTIVE = "active"
    LEAVING = "leaving"
    CLOSED = "closed"


@dataclass
class Session:
    id: str
    chat_id: int
    state: State = State.JOINING
    created_at: float = field(default_factory=time.time)
    audio_q: asyncio.Queue[bytes] = field(default_factory=lambda: asyncio.Queue(maxsize=256))
    ws: WebSocket | None = None
    _stop: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def stop_event(self) -> asyncio.Event:
        return self._stop

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "state": self.state.value,
            "created_at": self.created_at,
        }


class SessionManager:
    """Manages active relay sessions with capacity enforcement."""

    def __init__(self, max_sessions: int) -> None:
        self._max = max_sessions
        self._sessions: dict[str, Session] = {}

    def create(self, chat_id: int) -> Session:
        if len(self._sessions) >= self._max:
            raise RuntimeError(f"max sessions ({self._max}) reached")

        for s in self._sessions.values():
            if s.chat_id == chat_id and s.state not in (State.LEAVING, State.CLOSED):
                raise RuntimeError(f"session already active for chat {chat_id}")

        sid = uuid.uuid4().hex[:8]
        sess = Session(id=sid, chat_id=chat_id)
        self._sessions[sid] = sess
        return sess

    def get(self, sid: str) -> Session | None:
        return self._sessions.get(sid)

    def remove(self, sid: str) -> Session | None:
        return self._sessions.pop(sid, None)

    def list_all(self) -> list[Session]:
        return list(self._sessions.values())

    async def close_all(self) -> None:
        for s in list(self._sessions.values()):
            s.stop_event.set()
        self._sessions.clear()
