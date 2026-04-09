from __future__ import annotations

import json
from pathlib import Path

from .types import SignEntry, SignType


class SignDictionary:
    """Maps uppercase gloss tokens to sign metadata.

    The actual bone keyframes are Agent 3's artifact;
    Agent 4 only stores IDs and durations.
    """

    def __init__(self, path: str | Path | None = None):
        self._signs: dict[str, dict] = {}
        if path is None:
            return
        p = Path(path)
        if not p.exists():
            return
        try:
            raw = json.loads(p.read_text())
            for k, v in raw.items():
                self._signs[k.upper()] = v
        except (json.JSONDecodeError, OSError):
            pass

    def lookup(self, gloss: str) -> SignEntry | None:
        info = self._signs.get(gloss.upper())
        if info is None:
            return None
        return SignEntry(
            gloss=info["gloss"],
            type=SignType.SIGN,
            sign_id=info["sign_id"],
            duration_ms=info["duration_ms"],
        )

    def __len__(self) -> int:
        return len(self._signs)
