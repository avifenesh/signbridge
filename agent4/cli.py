#!/usr/bin/env python3
"""CLI for testing the ASL translation engine."""

import json
import sys
from pathlib import Path

from asl_engine.engine import Engine, Config
from asl_engine.types import STTOutput, LowConfidenceError

DATA = Path(__file__).resolve().parent / "data"


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python cli.py <sentence>", file=sys.stderr)
        sys.exit(1)

    sentence = " ".join(sys.argv[1:])

    eng = Engine(
        Config(
            patterns_path=DATA / "patterns.json",
            dictionary_path=DATA / "dictionary.json",
        )
    )

    try:
        result = eng.translate(
            STTOutput(sentence=sentence, confidence=0.95, source="cli")
        )
    except LowConfidenceError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
