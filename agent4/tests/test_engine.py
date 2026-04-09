"""Tests for the ASL translation engine — covers all 3 tiers, fingerspelling,
dictionary lookup, contract fixtures from the spec, and edge cases."""

from pathlib import Path

import pytest

from asl_engine.engine import Engine, Config
from asl_engine.types import STTOutput, SignType, LowConfidenceError
from asl_engine.normalize import normalize
from asl_engine.fingerspell import fingerspell
from asl_engine.dictionary import SignDictionary

DATA = Path(__file__).resolve().parent.parent / "data"
PATTERNS = DATA / "patterns.json"
DICTIONARY = DATA / "dictionary.json"


@pytest.fixture
def eng() -> Engine:
    return Engine(Config(patterns_path=PATTERNS, dictionary_path=DICTIONARY))


# --- normalize ---


@pytest.mark.parametrize(
    "inp, want",
    [
        ("Hello!", "hello"),
        ("  What is your name?  ", "what is your name"),
        ("I DON'T like that.", "i do not like that"),
        ("I can't believe it", "i can not believe it"),
        ("She's   here", "she is here"),
        ("I'm gonna go", "i am going to go"),
    ],
)
def test_normalize(inp: str, want: str) -> None:
    assert normalize(inp) == want


# --- fingerspell ---


def test_fingerspell_letters() -> None:
    s = fingerspell("Sarah")
    assert s.type == SignType.FINGERSPELL
    assert s.letters == ["S", "A", "R", "A", "H"]
    assert s.duration_ms == 1500


def test_fingerspell_digits() -> None:
    s = fingerspell("A1B2")
    assert s.letters == ["A", "1", "B", "2"]


# --- tier 1 ---


def test_tier1_gave_you_the_book(eng: Engine) -> None:
    out, ok = eng._tier1.translate("I gave you the book")
    assert ok
    assert out is not None
    assert out.asl_gloss == ["BOOK", "I", "GIVE-YOU"]
    assert out.method == "pattern_hash"
    assert out.confidence == 1.0


def test_tier1_what_is_your_name(eng: Engine) -> None:
    out, ok = eng._tier1.translate("What is your name?")
    assert ok
    assert out is not None
    assert out.asl_gloss == ["YOUR", "NAME", "WHAT"]


def test_tier1_contraction_expansion(eng: Engine) -> None:
    # "I don't like that" → "i do not like that" → matches "I do not like {OBJECT}"
    out, ok = eng._tier1.translate("I don't like that")
    assert ok
    assert out is not None
    # Verify it matched a negation pattern and produced valid ASL gloss
    assert "NOT" in out.asl_gloss
    assert "LIKE" in out.asl_gloss or "THAT" in out.asl_gloss


def test_tier1_no_slots(eng: Engine) -> None:
    out, ok = eng._tier1.translate("Thank you")
    assert ok
    assert out is not None
    assert out.asl_gloss == ["THANK-YOU"]


def test_tier1_no_match(eng: Engine) -> None:
    _, ok = eng._tier1.translate("The quick brown fox jumps over the lazy dog")
    assert not ok


# --- tier 2 ---


def test_tier2_similar_sentence(eng: Engine) -> None:
    out, ok = eng._tier2.translate("The weather looks nice today")
    assert ok
    assert out is not None
    assert out.method == "vector_similarity"
    assert out.confidence >= 0.75


def test_tier2_below_threshold(eng: Engine) -> None:
    _, ok = eng._tier2.translate("xylophone quantum zebra")
    assert not ok


# --- full engine ---


def test_engine_translate_tier1(eng: Engine) -> None:
    seq = eng.translate(
        STTOutput(sentence="I gave you the book", confidence=0.94, source="vosk")
    )
    assert seq.type == "sign_sequence"
    assert seq.english == "I gave you the book"
    assert seq.gloss == ["BOOK", "I", "GIVE-YOU"]
    # BOOK should come from dictionary
    assert seq.signs[0].type == SignType.SIGN
    assert seq.signs[0].sign_id == "book"
    # GIVE-YOU directional verb from dictionary
    assert seq.signs[2].type == SignType.SIGN


def test_engine_translate_fallback(eng: Engine) -> None:
    seq = eng.translate(
        STTOutput(sentence="xylophone quantum zebra", confidence=0.80, source="vosk")
    )
    assert len(seq.signs) == 3
    for s in seq.signs:
        assert s.type == SignType.FINGERSPELL


def test_engine_low_confidence(eng: Engine) -> None:
    with pytest.raises(LowConfidenceError) as exc_info:
        eng.translate(
            STTOutput(sentence="something something", confidence=0.2, source="vosk")
        )
    assert exc_info.value.threshold == 0.3


def test_engine_zero_confidence_passes(eng: Engine) -> None:
    # confidence=0 means "not set" — should pass through
    seq = eng.translate(
        STTOutput(sentence="Hello", confidence=0, source="cli")
    )
    assert seq.gloss == ["HELLO"]


# --- contract test fixtures from spec ---


@pytest.mark.parametrize(
    "sentence, want_gloss",
    [
        ("I gave you the book", ["BOOK", "I", "GIVE-YOU"]),
        ("What is your name?", ["YOUR", "NAME", "WHAT"]),
    ],
)
def test_contract_spec_examples(eng: Engine, sentence: str, want_gloss: list[str]) -> None:
    seq = eng.translate(STTOutput(sentence=sentence, confidence=0.94, source="test"))
    assert seq.gloss == want_gloss


def test_contract_output_format(eng: Engine) -> None:
    seq = eng.translate(
        STTOutput(sentence="I gave you the book", confidence=0.94, source="vosk")
    )
    assert seq.type == "sign_sequence"
    assert 0 < seq.pipeline_confidence <= 1.0
    assert len(seq.gloss) > 0
    assert len(seq.signs) > 0
    for s in seq.signs:
        assert s.gloss
        assert s.type in (SignType.SIGN, SignType.FINGERSPELL)
        assert s.duration_ms > 0


def test_contract_json_serialization(eng: Engine) -> None:
    seq = eng.translate(
        STTOutput(sentence="I gave you the book", confidence=0.94, source="vosk")
    )
    d = seq.to_dict()
    assert d["type"] == "sign_sequence"
    assert isinstance(d["signs"], list)
    assert d["signs"][0]["type"] == "sign"
    assert "sign_id" in d["signs"][0]


# --- dictionary ---


def test_dictionary_lookup() -> None:
    d = SignDictionary(DICTIONARY)
    assert len(d) > 0
    entry = d.lookup("BOOK")
    assert entry is not None
    assert entry.sign_id == "book"
    assert entry.duration_ms == 600


def test_dictionary_missing() -> None:
    d = SignDictionary()
    assert d.lookup("ANYTHING") is None


def test_dictionary_case_insensitive() -> None:
    d = SignDictionary(DICTIONARY)
    assert d.lookup("book") is not None
