"""Guard tokenizer and processor saves against unsafe chat template names.

Transformers 5.10.0 fixes GHSA-xrqw-3rrv-vx5w upstream. This guard stays as defense in
depth: it rejects path-like template names before any file is written, including the
tokenizer saves done by the ONNX exports and Trainer's epoch checkpoints. Install it
before starting export or training.
"""
from __future__ import annotations

from functools import wraps
from pathlib import PureWindowsPath
from threading import Lock

_INSTALL_LOCK = Lock()
_GUARD_MARKER = "_signbridge_chat_template_save_guard"


def _validate_template_names(template: object) -> None:
    if isinstance(template, dict):
        names = template.keys()
    elif isinstance(template, (list, tuple)):
        # Older tokenizer configurations store named templates as a list of dictionaries.
        names = [entry["name"] for entry in template]
    else:
        return

    for name in names:
        if (
            not isinstance(name, str)
            or not name
            or name in {".", ".."}
            or any(char in name for char in ("/", "\\", "\0", ":"))
            or PureWindowsPath(name).drive
        ):
            raise ValueError(f"Invalid chat template name: {name!r}")


def _guard_save(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        _validate_template_names(getattr(self, "chat_template", None))
        return method(self, *args, **kwargs)

    setattr(guarded, _GUARD_MARKER, True)
    return guarded


def _install_chat_template_save_guard() -> None:
    """Install once per class, with no restoration window between internal saves."""
    from transformers import ProcessorMixin
    from transformers.tokenization_utils_base import PreTrainedTokenizerBase

    with _INSTALL_LOCK:
        for cls in (PreTrainedTokenizerBase, ProcessorMixin):
            method = cls.save_pretrained
            if not getattr(method, _GUARD_MARKER, False):
                cls.save_pretrained = _guard_save(method)
