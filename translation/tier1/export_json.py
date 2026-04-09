"""
Export Tier 1 pattern table to JSON artifact for Android.

Output: app/src/main/assets/translation/patterns.json

The Android PatternHashTable reads this file instead of using hardcoded patterns.
Format matches what AslTranslationEngine.kt expects.

Usage:
    python -m translation.tier1.export_json
    # or via main export pipeline:
    python -m translation.export
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from translation.config import PATTERNS_JSON, ensure_dirs
from translation.tier1.patterns import PATTERNS


def export(output_path: Path = PATTERNS_JSON, *, verbose: bool = True) -> Path:
    """Write patterns.json and return the output path."""
    ensure_dirs()

    records = [
        {
            "english": p["english"],
            "asl": p["asl"],
            "category": p["category"],
        }
        for p in PATTERNS
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f"[tier1] Exported {len(records)} patterns → {output_path}")
        by_cat: dict[str, int] = {}
        for p in PATTERNS:
            by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1
        for cat, count in sorted(by_cat.items()):
            print(f"  {cat:20s} {count:3d} patterns")

    return output_path


def _verify_round_trip(output_path: Path) -> bool:
    """Sanity-check: reload JSON and verify slot parsing is consistent."""
    import re

    with open(output_path, encoding="utf-8") as f:
        records = json.load(f)

    errors = []
    for rec in records:
        english = rec["english"]
        asl = rec["asl"]
        eng_slots = set(re.findall(r"\{(\w+)\}", english))
        asl_slots = set(re.findall(r"\{(\w+)\}", asl))
        extra = asl_slots - eng_slots
        if extra:
            errors.append(f"  ASL slot {extra} not in English: '{english}' → '{asl}'")

    if errors:
        print("[tier1] Round-trip errors:")
        for e in errors:
            print(e)
        return False

    print(f"[tier1] Round-trip OK ({len(records)} patterns, no slot mismatches)")
    return True


if __name__ == "__main__":
    out = export()
    ok = _verify_round_trip(out)
    sys.exit(0 if ok else 1)
