"""ASL Translation Engine — CLI entry point.

Usage:
    python3 -m translation translate "I gave you the book"
    python3 -m translation batch sentences.txt
    python3 -m translation build-index
    python3 -m translation info
    python3 -m translation rules "What is your name?"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_translate(args: argparse.Namespace) -> None:
    """Translate English to ASL gloss using the full cascade."""
    from translation.engine import TranslationEngine

    engine = TranslationEngine()
    result = engine.translate(args.sentence)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        gloss_str = " ".join(result.asl_gloss)
        print(f"English: {args.sentence}")
        print(f"ASL:     {gloss_str}")
        print(f"Method:  {result.method.value} (confidence: {result.confidence:.2f})")
        if result.debug:
            for k, v in result.debug.items():
                print(f"  {k}: {v}")


def cmd_batch(args: argparse.Namespace) -> None:
    """Translate multiple sentences from a file (one per line)."""
    from translation.engine import TranslationEngine

    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    engine = TranslationEngine()
    lines = [l.strip() for l in path.read_text().splitlines() if l.strip()]

    results = []
    for line in lines:
        r = engine.translate(line)
        results.append(r.to_dict())
        gloss_str = " ".join(r.asl_gloss)
        method = r.method.value
        print(f"  [{method:10s} {r.confidence:.2f}] {line}")
        print(f"  {'':13s} → {gloss_str}")
        print()

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results written to: {out}")


def cmd_rules(args: argparse.Namespace) -> None:
    """Apply grammar rules only (no tier lookup) for debugging."""
    from translation.gloss.rules import apply_rules

    gloss = apply_rules(args.sentence)
    print(f"English: {args.sentence}")
    print(f"ASL:     {' '.join(gloss)}")
    print(f"Method:  rules_only")


def cmd_build_index(args: argparse.Namespace) -> None:
    """Build the FAISS index from the hash table data."""
    from translation.config import ARTIFACTS_DIR
    from translation.tier1.hash_table import HashTable
    from translation.tier2.similarity import SimilaritySearch

    print("Loading phrase table...")
    ht = HashTable()
    ht.load()

    # Collect all known sentence → gloss pairs for the index
    pairs = [(sentence, gloss) for sentence, gloss in ht.exact.items()]

    # Also expand patterns with their examples (if we had them)
    # For now, just use the exact matches
    print(f"  {len(pairs)} sentence-gloss pairs")

    print("Building FAISS index...")
    search = SimilaritySearch()
    output_dir = Path(args.output) if args.output else ARTIFACTS_DIR
    index_path, map_path = search.build_index(pairs, output_dir)
    print(f"  Index: {index_path} ({search.index_size} vectors)")
    print(f"  Metadata: {map_path}")


def cmd_info(args: argparse.Namespace) -> None:
    """Show translation engine status."""
    from translation.engine import TranslationEngine

    engine = TranslationEngine()
    stats = engine.stats()
    print("ASL Translation Engine")
    print("======================")
    print(f"Tier 1 (hash):       {stats['tier1']['exact_entries']} exact, "
          f"{stats['tier1']['pattern_entries']} patterns")
    print(f"Tier 2 (similarity): {stats['tier2']['index_size']} vectors indexed")
    print(f"Tier 3 (model):      {stats['tier3']['status']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="translation",
        description="SignBridge ASL Translation Engine",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # translate
    p_tr = sub.add_parser("translate", help="Translate English to ASL gloss")
    p_tr.add_argument("sentence", help="English sentence to translate")
    p_tr.add_argument("--json", action="store_true", help="Output as JSON")

    # batch
    p_batch = sub.add_parser("batch", help="Translate sentences from file")
    p_batch.add_argument("file", help="Text file with one sentence per line")
    p_batch.add_argument("--output", help="Save results to JSON file")

    # rules
    p_rules = sub.add_parser("rules", help="Apply grammar rules only (debug)")
    p_rules.add_argument("sentence", help="English sentence")

    # build-index
    p_idx = sub.add_parser("build-index", help="Build FAISS index from phrase table")
    p_idx.add_argument("--output", help="Output directory for index files")

    # info
    sub.add_parser("info", help="Show engine status")

    args = parser.parse_args()
    commands = {
        "translate": cmd_translate,
        "batch": cmd_batch,
        "rules": cmd_rules,
        "build-index": cmd_build_index,
        "info": cmd_info,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
