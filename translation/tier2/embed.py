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

from translation._tokenizer_security import _install_chat_template_save_guard


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
          token_type_ids : int64 [batch, seq] (when the tokenizer uses them)
        and produces:
          last_hidden_state : float32 [batch, seq, 384]

        This is the same layout the previous Optimum export produced. Android
        loads it via OnnxRuntime, tokenizes with the HuggingFace tokenizer
        (tokenizer.json bundled alongside), mean-pools over attention_mask and
        L2-normalizes.
        """
        if self._model is None:
            raise RuntimeError("Call load() before export_onnx()")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        _install_chat_template_save_guard()
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as e:
            raise ImportError(
                "torch and transformers are required. Run: pip install -r translation/requirements.txt"
            ) from e

        cache = str(self._model_cache) if self._model_cache else None
        tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME, cache_dir=cache)
        model = AutoModel.from_pretrained(self.MODEL_NAME, cache_dir=cache).eval()
        tokenizer.save_pretrained(str(output_path.parent))

        input_names = ["input_ids", "attention_mask"]
        if "token_type_ids" in tokenizer.model_input_names:
            input_names.append("token_type_ids")

        class Encoder(torch.nn.Module):
            def __init__(self, model):
                super().__init__()
                self.model = model

            def forward(self, *inputs):
                return self.model(**dict(zip(input_names, inputs)), return_dict=False)[0]

        dummy = [torch.ones((1, 8), dtype=torch.long) for _ in input_names]
        # Trace with a padded mask so the exported graph keeps the masking path.
        dummy[1][:, -2:] = 0
        dummy[2:] = [torch.zeros_like(t) for t in dummy[2:]]
        dynamic_axes = {name: {0: "batch", 1: "seq"} for name in input_names}
        dynamic_axes["last_hidden_state"] = {0: "batch", 1: "seq"}
        with torch.no_grad():
            torch.onnx.export(
                Encoder(model),
                tuple(dummy),
                str(output_path),
                input_names=input_names,
                output_names=["last_hidden_state"],
                dynamic_axes=dynamic_axes,
                opset_version=opset,
                dynamo=False,
            )

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
