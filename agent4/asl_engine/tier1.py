from __future__ import annotations

import json
import re
from pathlib import Path

from .normalize import normalize, fill_asl_template, build_slot_regex
from .types import TranslationOutput


class PatternEntry:
    __slots__ = ("pattern", "asl_template", "regex", "slot_names", "specificity")

    def __init__(self, pattern: str, asl_template: str):
        self.pattern = pattern
        self.asl_template = asl_template
        self.regex: re.Pattern
        self.slot_names: list[str]
        self.specificity: int
        self._compile()

    def _compile(self) -> None:
        regex, names = build_slot_regex(self.pattern)
        if regex is not None:
            self.regex = regex
            self.slot_names = names
        else:
            norm = normalize(self.pattern)
            self.regex = re.compile(f"^{re.escape(norm)}$")
            self.slot_names = []
        # Specificity = literal word count (more literal = more specific)
        self.specificity = len(self.pattern.split()) - len(self.slot_names)


class Tier1:
    """Pattern hash table with template slot extraction.

    When multiple patterns match, the most specific one wins
    (highest literal word count).
    """

    def __init__(self, path: str | Path):
        data = json.loads(Path(path).read_text())
        self.patterns = [
            PatternEntry(e["pattern"], e["asl_template"]) for e in data
        ]

    def translate(self, sentence: str) -> tuple[TranslationOutput | None, bool]:
        norm = normalize(sentence)
        best: tuple[PatternEntry, re.Match] | None = None
        best_spec = -1
        for p in self.patterns:
            m = p.regex.match(norm)
            if m is None:
                continue
            if p.specificity > best_spec:
                best_spec = p.specificity
                best = (p, m)
        if best is None:
            return None, False
        p, m = best
        slots = {k: v.upper() for k, v in m.groupdict().items()}
        gloss = fill_asl_template(p.asl_template, slots)
        return TranslationOutput(
            asl_gloss=gloss,
            method="pattern_hash",
            pattern=p.pattern,
            confidence=1.0,
        ), True
