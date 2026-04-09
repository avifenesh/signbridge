"""
Telegram call bridge — joins group calls via pytgcalls, captures incoming
audio and pushes raw PCM frames into session queues.

Uses pytgcalls' record() + stream_frame API, same mechanism as the official
whisper_transcription example.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from pyrogram import Client
from pytgcalls import PyTgCalls, filters
from pytgcalls.types import (
    AudioQuality,
    Device,
    Direction,
    RecordStream,
    StreamFrames,
)

if TYPE_CHECKING:
    from session import Session

log = logging.getLogger("bridge")


class CallBridge:
    """Wraps pyrogram + pytgcalls to join Telegram group calls and capture audio."""

    def __init__(
        self,
        app_id: str,
        app_hash: str,
        phone: str,
        session_file: str,
    ) -> None:
        self._client = Client(
            name=session_file,
            api_id=int(app_id),
            api_hash=app_hash,
            phone_number=phone,
        )
        self._calls = PyTgCalls(self._client)
        self._sessions: dict[int, Session] = {}
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        await self._client.start()
        await self._calls.start()

        # Single global handler — routes incoming audio frames to the correct
        # session via the chat_id → Session map.
        @self._calls.on_update(
            filters.stream_frame(Direction.INCOMING, Device.MICROPHONE),
        )
        async def _on_frame(_: PyTgCalls, update: StreamFrames) -> None:
            sess = self._sessions.get(update.chat_id)
            if sess is None:
                return
            for frame_data in update.frames:
                try:
                    sess.audio_q.put_nowait(frame_data.frame)
                except asyncio.QueueFull:
                    pass  # drop if WS consumer is slow

        self._started = True
        log.info("telegram client started")

    async def stop(self) -> None:
        if not self._started:
            return
        await self._calls.stop()
        await self._client.stop()
        self._sessions.clear()
        self._started = False
        log.info("telegram client stopped")

    async def join(self, session: Session) -> None:
        """Join the group call for *session.chat_id*, capture audio into
        *session.audio_q* until *session.stop_event* is set."""
        from session import State

        chat_id = session.chat_id
        self._sessions[chat_id] = session
        log.info("joining group call chat=%d session=%s", chat_id, session.id)

        await self._calls.record(
            chat_id,
            RecordStream(True, AudioQuality.HIGH),
        )
        session.state = State.ACTIVE
        log.info("capturing audio session=%s", session.id)

        await session.stop_event.wait()

        log.info("leaving group call session=%s", session.id)
        self._sessions.pop(chat_id, None)
        await self._calls.leave_group_call(chat_id)
        session.state = State.CLOSED
