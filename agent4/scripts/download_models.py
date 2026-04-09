#!/usr/bin/env python3
"""Download MiniLM-L6-v2 ONNX model and vocab for tier 2 embeddings.

Downloads from HuggingFace model hub into models/ directory.
Total size: ~23MB (model) + ~230KB (vocab).
"""
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

FILES = {
    "model.onnx": (
        "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/"
        "resolve/main/onnx/model.onnx"
    ),
    "vocab.txt": (
        "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/"
        "resolve/main/vocab.txt"
    ),
}


def download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"  skip {dest.name} (exists)")
        return
    print(f"  downloading {dest.name} ...")
    urllib.request.urlretrieve(url, dest)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  saved {dest.name} ({size_mb:.1f} MB)")


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading MiniLM-L6-v2 to {MODELS_DIR}/")
    for name, url in FILES.items():
        download(url, MODELS_DIR / name)
    print("Done. Tier 2 embedder ready.")


if __name__ == "__main__":
    main()
