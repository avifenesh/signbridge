import os
from unittest.mock import patch

import pytest

from config import Config


def test_defaults():
    with patch.dict(os.environ, {"TELEGRAM_APP_ID": "1", "TELEGRAM_APP_HASH": "h"}):
        cfg = Config()
        cfg.telegram_app_id = "1"
        cfg.telegram_app_hash = "h"
        cfg.validate()
        assert cfg.listen_port == 8080
        assert cfg.max_sessions == 5
        assert cfg.sample_rate == 16000


def test_validate_missing_app_id():
    cfg = Config()
    cfg.telegram_app_id = ""
    cfg.telegram_app_hash = ""
    with pytest.raises(RuntimeError, match="TELEGRAM_APP_ID"):
        cfg.validate()


def test_frame_bytes():
    cfg = Config()
    # 16kHz, 20ms, mono, 16-bit: 320 samples * 2 bytes = 640
    assert cfg.frame_bytes == 640
