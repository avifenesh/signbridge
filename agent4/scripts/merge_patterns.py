#!/usr/bin/env python3
"""Merge translation/ patterns into agent4 patterns.json.

Plan:
  1. Start with agent4's patterns (canonical format)
  2. Add patterns only in translation/ (converted to agent4 format)
  3. For gloss conflicts on overlapping patterns, prefer translation/ glosses
     (more ASL-linguistically correct: topic-comment, YOU HOW YOU not YOU HOW)
  4. Run eval to verify nothing breaks

Run from signbridge/agent4/:
  python3 scripts/merge_patterns.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIGNBRIDGE = ROOT.parent

sys.path.insert(0, str(SIGNBRIDGE))
from translation.tier1.patterns import PATTERNS as TRANS_PATTERNS


def normalize_key(english: str) -> str:
    """Normalize pattern text for comparison (lowercase, strip punct, collapse ws)."""
    s = english.lower().strip().rstrip(".!?,;:")
    return " ".join(s.split())


def main() -> None:
    # Load agent4 patterns
    agent4_path = ROOT / "data" / "patterns.json"
    agent4_raw = json.loads(agent4_path.read_text())
    print(f"agent4 patterns: {len(agent4_raw)}")

    # Build lookup: normalized english → agent4 entry
    agent4_map: dict[str, dict] = {}
    for entry in agent4_raw:
        key = normalize_key(entry["pattern"])
        agent4_map[key] = entry

    # Build lookup: normalized english → translation entry
    trans_map: dict[str, dict] = {}
    for tp in TRANS_PATTERNS:
        key = normalize_key(tp["english"])
        trans_map[key] = {
            "pattern": tp["english"],
            "asl_template": tp["asl"],
        }
    print(f"translation/ patterns: {len(trans_map)}")

    # Find overlap and conflicts
    overlap_keys = set(agent4_map) & set(trans_map)
    only_agent4 = set(agent4_map) - set(trans_map)
    only_trans = set(trans_map) - set(agent4_map)
    print(f"Overlap: {len(overlap_keys)}")
    print(f"Only in agent4: {len(only_agent4)}")
    print(f"Only in translation/: {len(only_trans)}")

    conflicts = 0
    for key in sorted(overlap_keys):
        a4_gloss = agent4_map[key]["asl_template"]
        tr_gloss = trans_map[key]["asl_template"]
        if a4_gloss.upper().strip() != tr_gloss.upper().strip():
            conflicts += 1
            print(f"  CONFLICT: '{key}'")
            print(f"    agent4:      {a4_gloss}")
            print(f"    translation: {tr_gloss}")
    print(f"Gloss conflicts: {conflicts}")

    # Merge: agent4 base + translation overrides for conflicts + translation-only
    merged: list[dict] = []

    # 1. Agent4 patterns, with translation/ gloss for conflicts
    for entry in agent4_raw:
        key = normalize_key(entry["pattern"])
        if key in trans_map:
            tr = trans_map[key]
            # Prefer translation/ gloss (more ASL-correct)
            merged.append({
                "pattern": entry["pattern"],  # keep agent4 casing
                "asl_template": tr["asl_template"],
            })
        else:
            merged.append(entry)

    # 2. Add translation-only patterns
    for key in sorted(only_trans):
        tr = trans_map[key]
        merged.append({
            "pattern": tr["pattern"],
            "asl_template": tr["asl_template"],
        })

    print(f"\nMerged total: {len(merged)}")

    # Write
    agent4_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    print(f"Written to {agent4_path}")


if __name__ == "__main__":
    main()
