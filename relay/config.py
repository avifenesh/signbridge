from __future__ import annotations

import os


class Config:
    """Env-based configuration for the relay server."""

    listen_host: str = os.getenv("LISTEN_HOST", "0.0.0.0")
    listen_port: int = int(os.getenv("LISTEN_PORT", "8080"))
    max_sessions: int = int(os.getenv("MAX_SESSIONS", "5"))

    telegram_phone: str = os.getenv("TELEGRAM_PHONE", "")
    telegram_app_id: str = os.getenv("TELEGRAM_APP_ID", "")
    telegram_app_hash: str = os.getenv("TELEGRAM_APP_HASH", "")
    session_file: str = os.getenv("SESSION_FILE", "session")

    sample_rate: int = int(os.getenv("SAMPLE_RATE", "16000"))
    channels: int = 1
    frame_ms: int = int(os.getenv("FRAME_SIZE_MS", "20"))

    @property
    def frame_bytes(self) -> int:
        """Byte size of one PCM 16-bit audio frame."""
        samples = self.sample_rate * self.frame_ms // 1000
        return samples * 2 * self.channels

    def validate(self) -> None:
        if not self.telegram_app_id or not self.telegram_app_hash:
            raise RuntimeError("TELEGRAM_APP_ID and TELEGRAM_APP_HASH are required")


cfg = Config()
