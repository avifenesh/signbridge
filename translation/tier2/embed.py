"""
Tier 2: MiniLM-L6 sentence embedding.

Wraps sentence-transformers to produce 384-dim vectors.
Also handles ONNX export of the embedding model for Android.

Android uses the ONNX model + Android ONNX Runtime to embed query sentences
on-device, then queries the bundled FAISS index.
"""
from __future__ import annotations

import numpy as np
from pathlib import Path


class MiniLMEmbedder:
    """Sentence embedder using all-MiniLM-L6-v2."""

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    DIM = 384

    def __init__(self, model_cache: Path | None = None) -> None:
        self._model = None
        self._model_cache = model_cache

    def load(self) -> "MiniLMEmbedder":
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers not installed. Run: pip install sentence-transformers"
            ) from e

        kwargs = {}
        if self._model_cache:
            kwargs["cache_folder"] = str(self._model_cache)

        self._model = SentenceTransformer(self.MODEL_NAME, **kwargs)
        return self

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def embed(self, sentences: list[str]) -> np.ndarray:
        """Return (N, 384) float32 embeddings, L2-normalized."""
        if self._model is None:
            raise RuntimeError("Call load() before embed()")
        vecs = self._model.encode(
            sentences,
            convert_to_numpy=True,
            normalize_embeddings=True,   # unit-norm → cosine sim = dot product
            show_progress_bar=len(sentences) > 100,
        )
        return vecs.astype(np.float32)

    def embed_one(self, sentence: str) -> np.ndarray:
        """Return (384,) float32 vector for a single sentence."""
        return self.embed([sentence])[0]

    def export_onnx(self, output_path: Path, *, opset: int = 14) -> Path:
        """Export the transformer + pooling to a single ONNX file.

        The exported model accepts:
          input_ids      : int64 [batch, seq]
          attention_mask : int64 [batch, seq]
        and produces:
          sentence_embedding : float32 [batch, 384]

        Android loads this via OnnxRuntime, tokenizes with the HuggingFace
        tokenizer (tokenizer.json bundled alongside), and calls normalize().
        """
        if self._model is None:
            raise RuntimeError("Call load() before export_onnx()")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from optimum.onnxruntime import ORTModelForFeatureExtraction
            from transformers import AutoTokenizer
        except ImportError as e:
            raise ImportError(
                "optimum[onnxruntime] not installed. Run: pip install optimum[onnxruntime]"
            ) from e

        cache = str(self._model_cache) if self._model_cache else None
        ort_model = ORTModelForFeatureExtraction.from_pretrained(
            self.MODEL_NAME,
            export=True,
            cache_dir=cache,
        )
        tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME, cache_dir=cache)

        ort_model.save_pretrained(str(output_path.parent))
        tokenizer.save_pretrained(str(output_path.parent))

        # Rename the default model.onnx to our expected name
        default = output_path.parent / "model.onnx"
        if default.exists() and default != output_path:
            default.rename(output_path)

        print(f"[tier2] MiniLM ONNX exported → {output_path}")
        return output_path

    def quantize_onnx(self, input_path: Path, output_path: Path) -> Path:
        """Quantize ONNX model to INT8 for smaller Android bundle."""
        try:
            from onnxruntime.quantization import quantize_dynamic, QuantType
        except ImportError as e:
            raise ImportError("onnxruntime not installed") from e

        quantize_dynamic(
            str(input_path),
            str(output_path),
            weight_type=QuantType.QInt8,
        )
        size_before = input_path.stat().st_size / 1e6
        size_after = output_path.stat().st_size / 1e6
        print(
            f"[tier2] Quantized {input_path.name}: "
            f"{size_before:.1f}MB → {size_after:.1f}MB"
        )
        return output_path
