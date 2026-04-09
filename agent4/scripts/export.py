#!/usr/bin/env python3
"""Export artifacts for Android integration.

Outputs to build/ directory:
  - patterns.bin     — binary pattern hash table
  - dictionary.bin   — binary sign metadata
  - manifest.json    — version, checksums, sizes
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"


def export_patterns(patterns_path: Path, out_path: Path) -> int:
    """Export patterns as length-prefixed JSON entries in a binary file.

    Format: [count:u32] [entry_len:u32 entry_json:bytes] ...
    """
    patterns = json.loads(patterns_path.read_text())
    with open(out_path, "wb") as f:
        f.write(struct.pack("<I", len(patterns)))
        for p in patterns:
            data = json.dumps(p, separators=(",", ":")).encode("utf-8")
            f.write(struct.pack("<I", len(data)))
            f.write(data)
    return len(patterns)


def export_dictionary(dict_path: Path, out_path: Path) -> int:
    """Export dictionary as length-prefixed JSON entries."""
    entries = json.loads(dict_path.read_text())
    with open(out_path, "wb") as f:
        f.write(struct.pack("<I", len(entries)))
        for key, val in entries.items():
            entry = {"key": key, **val}
            data = json.dumps(entry, separators=(",", ":")).encode("utf-8")
            f.write(struct.pack("<I", len(data)))
            f.write(data)
    return len(entries)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    data = ROOT / "data"

    # Export patterns
    pat_out = BUILD / "patterns.bin"
    n_pat = export_patterns(data / "patterns.json", pat_out)
    print(f"Exported {n_pat} patterns → {pat_out} ({pat_out.stat().st_size} bytes)")

    # Export dictionary
    dict_out = BUILD / "dictionary.bin"
    n_dict = export_dictionary(data / "dictionary.json", dict_out)
    print(f"Exported {n_dict} signs → {dict_out} ({dict_out.stat().st_size} bytes)")

    # Copy ONNX models if present
    models = ROOT / "models"
    artifacts = [
        {"name": "patterns.bin", "path": str(pat_out), "sha256": sha256(pat_out)},
        {"name": "dictionary.bin", "path": str(dict_out), "sha256": sha256(dict_out)},
    ]
    for model_file in ["model.onnx", "vocab.txt"]:
        src = models / model_file
        if src.exists():
            dst = BUILD / model_file
            dst.write_bytes(src.read_bytes())
            artifacts.append({
                "name": model_file,
                "path": str(dst),
                "sha256": sha256(dst),
            })
            print(f"Copied {model_file} → {dst}")

    # Manifest
    manifest = {
        "version": "0.1.0",
        "patterns_count": n_pat,
        "dictionary_count": n_dict,
        "artifacts": [
            {**a, "size_bytes": Path(a["path"]).stat().st_size}
            for a in artifacts
        ],
    }
    manifest_path = BUILD / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest → {manifest_path}")
    total = sum(Path(a["path"]).stat().st_size for a in artifacts)
    print(f"Total export size: {total / 1024:.1f} KB")


if __name__ == "__main__":
    main()
