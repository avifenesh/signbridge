"""MiniLM-L6-v2 sentence embedder via ONNX Runtime.

Requires: onnxruntime, numpy
Model + vocab downloaded by scripts/download_models.py
"""
from __future__ import annotations

import math
from pathlib import Path

try:
    import numpy as np
    import onnxruntime as ort

    _HAS_ONNX = True
except ImportError:
    _HAS_ONNX = False


class WordPieceTokenizer:
    """Minimal BERT-compatible WordPiece tokenizer."""

    def __init__(self, vocab_path: str | Path):
        self.vocab: dict[str, int] = {}
        with open(vocab_path, encoding="utf-8") as f:
            for idx, line in enumerate(f):
                self.vocab[line.strip()] = idx
        self.unk_id = self.vocab.get("[UNK]", 0)
        self.cls_id = self.vocab.get("[CLS]", 101)
        self.sep_id = self.vocab.get("[SEP]", 102)
        self.pad_id = self.vocab.get("[PAD]", 0)

    def tokenize(
        self, text: str, max_length: int = 128
    ) -> dict[str, list[int]]:
        text = text.lower().strip()
        tokens: list[str] = []
        for word in _pre_tokenize(text):
            sub = self._wordpiece(word)
            tokens.extend(sub)

        tokens = tokens[: max_length - 2]
        ids = (
            [self.cls_id]
            + [self.vocab.get(t, self.unk_id) for t in tokens]
            + [self.sep_id]
        )
        attn = [1] * len(ids)
        pad = max_length - len(ids)
        ids += [self.pad_id] * pad
        attn += [0] * pad
        return {
            "input_ids": ids,
            "attention_mask": attn,
            "token_type_ids": [0] * max_length,
        }

    def _wordpiece(self, word: str) -> list[str]:
        if word in self.vocab:
            return [word]
        pieces: list[str] = []
        start = 0
        while start < len(word):
            end = len(word)
            found = False
            while start < end:
                sub = word[start:end]
                candidate = ("##" + sub) if start > 0 else sub
                if candidate in self.vocab:
                    pieces.append(candidate)
                    start = end
                    found = True
                    break
                end -= 1
            if not found:
                pieces.append("[UNK]")
                break
        return pieces


def _pre_tokenize(text: str) -> list[str]:
    """Split on whitespace and punctuation boundaries."""
    tokens: list[str] = []
    buf: list[str] = []
    for ch in text:
        if ch.isalnum():
            buf.append(ch)
        else:
            if buf:
                tokens.append("".join(buf))
                buf = []
            if not ch.isspace():
                tokens.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


class MiniLMEmbedder:
    """Production embedder using MiniLM-L6-v2 ONNX model (384-dim).

    Raises RuntimeError if onnxruntime/numpy are not installed.
    """

    def __init__(
        self,
        model_path: str | Path,
        vocab_path: str | Path,
        max_length: int = 128,
    ):
        if not _HAS_ONNX:
            raise RuntimeError(
                "onnxruntime and numpy required: pip install onnxruntime numpy"
            )
        self._session = ort.InferenceSession(
            str(model_path), providers=["CPUExecutionProvider"]
        )
        self._tokenizer = WordPieceTokenizer(vocab_path)
        self._max_length = max_length
        self._dims = 384

    @property
    def dims(self) -> int:
        return self._dims

    def embed(self, text: str) -> list[float]:
        tok = self._tokenizer.tokenize(text, self._max_length)
        inputs = {
            "input_ids": np.array([tok["input_ids"]], dtype=np.int64),
            "attention_mask": np.array([tok["attention_mask"]], dtype=np.int64),
            "token_type_ids": np.array([tok["token_type_ids"]], dtype=np.int64),
        }
        outputs = self._session.run(None, inputs)
        # outputs[0] shape: [1, seq_len, 384] — mean pool over tokens
        hidden = outputs[0][0]  # [seq_len, 384]
        mask = np.array(tok["attention_mask"], dtype=np.float32)
        mask_expanded = mask[:, np.newaxis]  # [seq_len, 1]
        summed = (hidden * mask_expanded).sum(axis=0)
        count = mask.sum()
        pooled = summed / max(count, 1)
        # L2-normalize
        norm = np.linalg.norm(pooled)
        if norm > 0:
            pooled = pooled / norm
        return pooled.tolist()


def try_load_minilm(
    models_dir: str | Path,
) -> MiniLMEmbedder | None:
    """Try to load MiniLM from standard paths. Returns None if not available."""
    d = Path(models_dir)
    model = d / "model.onnx"
    vocab = d / "vocab.txt"
    if not model.exists() or not vocab.exists():
        return None
    try:
        return MiniLMEmbedder(model, vocab)
    except Exception:
        return None
