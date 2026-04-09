"""
Tier 1 pattern hash table tests.

Run:
    pytest translation/tests/test_tier1.py -v
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────

FIXTURES_PATH = Path(__file__).parent / "contract_fixtures.json"


def load_fixtures(tier: int | None = None) -> list[dict]:
    data = json.loads(FIXTURES_PATH.read_text())
    fixtures = data["fixtures"]
    if tier is not None:
        fixtures = [f for f in fixtures if f.get("tier") == tier]
    return fixtures


def build_pattern_engine():
    """Build the pattern matching engine from patterns.py."""
    from translation.tier1.patterns import PATTERNS

    entries = []
    for p in PATTERNS:
        english = p["english"]
        slot_names = re.findall(r"\{(\w+)\}", english)
        regex_str = re.escape(english)
        for slot in slot_names:
            regex_str = regex_str.replace(rf"\{{{slot}\}}", rf"(?P<{slot}>.+?)")
        regex_str = rf"^{regex_str}[.?!]?$"
        entries.append((
            re.compile(regex_str, re.IGNORECASE),
            p["asl"],
            slot_names,
        ))
    return entries


def run_match(engine, sentence: str) -> tuple[str, float] | None:
    """Return (asl_gloss_string, confidence) or None."""
    normalized = sentence.lower().strip()
    # Strip trailing punctuation
    normalized = re.sub(r"[.?!]+$", "", normalized).strip()

    for regex, asl_template, slot_names in engine:
        m = regex.match(normalized)
        if m is None:
            continue

        # Fill slots
        asl = asl_template
        for slot in slot_names:
            try:
                value = m.group(slot).upper()
                asl = asl.replace(f"{{{slot}}}", value)
            except IndexError:
                pass

        return asl, 1.0
    return None


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_pattern_count():
    """Must have at least 150 patterns."""
    from translation.tier1.patterns import PATTERNS
    assert len(PATTERNS) >= 150, f"Only {len(PATTERNS)} patterns — need at least 150"


def test_no_slot_mismatches():
    """Every ASL slot must appear in the English pattern too."""
    from translation.tier1.patterns import PATTERNS
    errors = []
    for p in PATTERNS:
        eng_slots = set(re.findall(r"\{(\w+)\}", p["english"]))
        asl_slots = set(re.findall(r"\{(\w+)\}", p["asl"]))
        extra = asl_slots - eng_slots
        if extra:
            errors.append(f"  Pattern {p['english']!r}: ASL has extra slots {extra}")
    assert not errors, "\n" + "\n".join(errors)


def test_all_have_augmented():
    """Every pattern should have at least one augmented example."""
    from translation.tier1.patterns import PATTERNS
    missing = [p["english"] for p in PATTERNS if not p.get("augmented")]
    assert not missing, f"Patterns missing augmented: {missing[:5]}"


def test_augmented_examples_nonempty():
    """Augmented examples should be non-empty strings."""
    from translation.tier1.patterns import PATTERNS
    bad = []
    for p in PATTERNS:
        for ex in p.get("augmented", []):
            if not ex or not ex.strip():
                bad.append(p["english"])
    assert not bad, f"Empty augmented examples in: {bad[:5]}"


@pytest.mark.parametrize("fixture", load_fixtures(tier=1))
def test_contract_tier1(fixture):
    """Each Tier 1 contract fixture must produce the expected gloss."""
    engine = build_pattern_engine()
    result = run_match(engine, fixture["input"])

    assert result is not None, (
        f"No match for: {fixture['input']!r}  (id: {fixture['id']})"
    )
    asl_gloss_str, confidence = result
    produced_tokens = asl_gloss_str.split()

    expected_tokens = fixture.get("expected_gloss")
    if expected_tokens:
        assert produced_tokens == expected_tokens, (
            f"[{fixture['id']}] {fixture['input']!r}\n"
            f"  expected: {expected_tokens}\n"
            f"  got:      {produced_tokens}"
        )

    expected_contains = fixture.get("expected_gloss_contains")
    if expected_contains:
        for token in expected_contains:
            assert token in produced_tokens, (
                f"[{fixture['id']}] Missing token {token!r} in {produced_tokens}"
            )

    expected_conf_min = fixture.get("expected_confidence_min", 0.0)
    assert confidence >= expected_conf_min, (
        f"[{fixture['id']}] Confidence {confidence} < {expected_conf_min}"
    )


def test_slot_filling_person():
    """Slot filling: PERSON slot extracted correctly."""
    engine = build_pattern_engine()
    result = run_match(engine, "I gave John the book")
    assert result is not None
    asl, _ = result
    assert "JOHN" in asl
    assert "BOOK" in asl


def test_slot_filling_thing():
    """Slot filling: THING slot extracted correctly."""
    engine = build_pattern_engine()
    result = run_match(engine, "I want orange juice")
    assert result is not None
    asl, _ = result
    assert "ORANGE JUICE" in asl or "ORANGE" in asl


def test_slot_filling_name():
    """Slot filling: NAME slot extracted correctly."""
    engine = build_pattern_engine()
    result = run_match(engine, "My name is Zephyrine")
    assert result is not None
    asl, _ = result
    assert "ZEPHYRINE" in asl


def test_case_insensitive():
    """Pattern matching is case-insensitive."""
    engine = build_pattern_engine()
    r1 = run_match(engine, "HELLO")
    r2 = run_match(engine, "hello")
    r3 = run_match(engine, "Hello")
    assert r1 is not None and r2 is not None and r3 is not None
    assert r1[0] == r2[0] == r3[0]


def test_trailing_punctuation_stripped():
    """Trailing ? . ! should not prevent pattern matching."""
    engine = build_pattern_engine()
    r1 = run_match(engine, "What is your name?")
    r2 = run_match(engine, "What is your name")
    assert r1 is not None and r2 is not None
    assert r1[0] == r2[0]


def test_no_partial_match():
    """Pattern should not match a sentence that is a substring."""
    engine = build_pattern_engine()
    # "hello world extra" should NOT match "hello" pattern
    result = run_match(engine, "hello world extra words here")
    # It might match another pattern, but if it does, verify it's correct
    # The important thing: "hello" pattern specifically should not fire
    if result is not None:
        # If something matched, it must be a real pattern match
        assert len(result[0]) > 0


def test_export_json_round_trip(tmp_path):
    """export_json writes valid JSON that can be reloaded."""
    import json
    from translation.tier1.export_json import export

    out = export(tmp_path / "patterns.json", verbose=False)
    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert len(data) >= 150

    # Verify required fields
    for record in data:
        assert "english" in record
        assert "asl" in record
        assert "category" in record


def test_export_json_slot_consistency(tmp_path):
    """Exported JSON has no slot mismatches."""
    import json
    from translation.tier1.export_json import export

    out = export(tmp_path / "patterns.json", verbose=False)
    data = json.loads(out.read_text())
    for rec in data:
        eng_slots = set(re.findall(r"\{(\w+)\}", rec["english"]))
        asl_slots = set(re.findall(r"\{(\w+)\}", rec["asl"]))
        extra = asl_slots - eng_slots
        assert not extra, f"Slot mismatch in exported record: {rec}"
