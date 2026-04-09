"""
ASLG-PC12 dataset loader.

IMPORTANT: This dataset requires license verification before use.
See data/sources.md — status: PENDING VERIFICATION.

If you have obtained the dataset and verified the license:
  1. Place the data file at: .translation_cache/data/aslg_pc12/aslg_pc12.txt
  2. Update sources.md with the license confirmation date
  3. Run: python -m translation.data.aslg_pc12 --verify

Format of the raw file (tab-separated):
  ENGLISH_SENTENCE \\t ASL_GLOSS_SEQUENCE

Example:
  i gave you the book \\t BOOK I GIVE-YOU
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from translation.config import DATA_CACHE


RAW_FILE = DATA_CACHE / "aslg_pc12" / "aslg_pc12.txt"
OUTPUT_FILE = DATA_CACHE / "aslg_pc12" / "aslg_pc12_clean.jsonl"

# Quality filters
MIN_TOKENS = 2
MAX_TOKENS = 20


def load_raw(path: Path = RAW_FILE) -> list[tuple[str, str]]:
    """Load raw ASLG-PC12 file → list of (english, asl) pairs."""
    if not path.exists():
        raise FileNotFoundError(
            f"ASLG-PC12 raw file not found at {path}.\n"
            "  1. Obtain the dataset from http://www.achrafothman.net/site/asl-sgd.php\n"
            "  2. Verify the license (see data/sources.md)\n"
            f"  3. Place the file at {path}"
        )

    pairs = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            english, asl = parts[0].strip(), parts[1].strip()
            if english and asl:
                pairs.append((english, asl))

    return pairs


def normalize_english(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s']", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_asl(gloss: str) -> str:
    """Uppercase gloss tokens, normalize hyphenation."""
    gloss = gloss.upper().strip()
    # Collapse multiple spaces
    gloss = re.sub(r"\s+", " ", gloss)
    # Remove stray punctuation except hyphens (which are part of sign names)
    gloss = re.sub(r"[^\w\s\-]", "", gloss)
    return gloss


def quality_filter(english: str, asl: str) -> bool:
    """Return True if the pair passes quality filters."""
    eng_tokens = english.split()
    asl_tokens = asl.split()
    if len(eng_tokens) < MIN_TOKENS or len(eng_tokens) > MAX_TOKENS:
        return False
    if len(asl_tokens) < MIN_TOKENS or len(asl_tokens) > MAX_TOKENS:
        return False
    # Reject if ASL gloss contains lowercase (likely parsing error)
    if any(t != t.upper() for t in asl_tokens if t.isalpha()):
        return False
    return True


def process(
    input_path: Path = RAW_FILE,
    output_path: Path = OUTPUT_FILE,
    *,
    verbose: bool = True,
) -> Path:
    """
    Load, clean, and deduplicate ASLG-PC12.
    Writes a JSONL file with {english, asl, source, confidence} records.
    Returns output path.
    """
    raw = load_raw(input_path)
    if verbose:
        print(f"[aslg_pc12] Loaded {len(raw)} raw pairs")

    seen = set()
    records = []
    filtered = 0
    duplicates = 0

    for english, asl in raw:
        eng_norm = normalize_english(english)
        asl_norm = normalize_asl(asl)

        if not quality_filter(eng_norm, asl_norm):
            filtered += 1
            continue

        key = eng_norm
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)

        records.append({
            "english": eng_norm,
            "asl": asl_norm,
            "source": "aslg_pc12",
            "confidence": 0.8,  # auto-generated, not native-validated
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if verbose:
        print(f"[aslg_pc12] Processed: {len(records)} clean pairs")
        print(f"  Filtered (length/quality): {filtered}")
        print(f"  Duplicates removed: {duplicates}")
        print(f"  Output → {output_path}")

    return output_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RAW_FILE)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    parser.add_argument("--verify", action="store_true",
                        help="Just count and sample the raw file without writing output")
    args = parser.parse_args()

    if args.verify:
        pairs = load_raw(args.input)
        print(f"Raw pairs: {len(pairs)}")
        for eng, asl in pairs[:5]:
            print(f"  {eng!r} → {asl!r}")
        sys.exit(0)

    process(args.input, args.output)
