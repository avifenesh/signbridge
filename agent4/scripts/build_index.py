#!/usr/bin/env python3
"""Build a pre-computed embedding index from patterns.

Embeds every pattern using MiniLM and saves the vectors for fast loading.
Output: data/pattern_embeddings.json

This avoids re-embedding all patterns on every engine startup.
With the BagOfWords fallback, embedding is instant; with MiniLM, it takes
a few seconds for hundreds of patterns.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from asl_engine.embedder_minilm import try_load_minilm
from asl_engine.tier2 import BagOfWordsEmbedder


def main() -> None:
    patterns_path = ROOT / "data" / "patterns.json"
    output_path = ROOT / "data" / "pattern_embeddings.json"
    models_dir = ROOT / "models"

    patterns = json.loads(patterns_path.read_text())
    print(f"Loaded {len(patterns)} patterns")

    # Try MiniLM first, fall back to BoW
    embedder = try_load_minilm(models_dir)
    if embedder is not None:
        print("Using MiniLM-L6-v2 embedder")
        name = "minilm"
    else:
        print("MiniLM not found, using BagOfWords (run download_models.py first for production)")
        embedder = BagOfWordsEmbedder(384)
        name = "bow"

    entries = []
    for i, p in enumerate(patterns):
        vec = embedder.embed(p["pattern"])
        entries.append({
            "pattern": p["pattern"],
            "asl_template": p["asl_template"],
            "embedding": vec,
        })
        if (i + 1) % 50 == 0:
            print(f"  embedded {i + 1}/{len(patterns)}")

    output = {
        "embedder": name,
        "dims": embedder.dims,
        "count": len(entries),
        "entries": entries,
    }
    output_path.write_text(json.dumps(output))
    size_kb = output_path.stat().st_size / 1024
    print(f"Saved {len(entries)} embeddings to {output_path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
