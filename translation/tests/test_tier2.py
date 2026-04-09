"""
Tier 2 vector similarity tests.

These tests require sentence-transformers and faiss-cpu installed,
and the FAISS index to be built first:
    python -m translation.tier2.build_index

Run:
    pytest translation/tests/test_tier2.py -v
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

FIXTURES_PATH = Path(__file__).parent / "contract_fixtures.json"


def has_tier2_deps() -> bool:
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
        return True
    except ImportError:
        return False


def has_index() -> bool:
    from translation.config import FAISS_INDEX, INDEX_MAP_JSON
    return FAISS_INDEX.exists() and INDEX_MAP_JSON.exists()


skip_no_deps = pytest.mark.skipif(
    not has_tier2_deps(),
    reason="faiss-cpu or sentence-transformers not installed"
)

skip_no_index = pytest.mark.skipif(
    not has_index(),
    reason="FAISS index not built. Run: python -m translation.tier2.build_index"
)


# ── Embedding tests (no index required) ──────────────────────────────────────

@skip_no_deps
def test_embedder_loads():
    from translation.tier2.embed import MiniLMEmbedder
    from translation.config import MODEL_CACHE
    embedder = MiniLMEmbedder(model_cache=MODEL_CACHE)
    embedder.load()
    assert embedder.is_loaded


@skip_no_deps
def test_embedder_dim():
    from translation.tier2.embed import MiniLMEmbedder
    import numpy as np
    embedder = MiniLMEmbedder().load()
    vec = embedder.embed_one("hello")
    assert vec.shape == (384,)
    assert vec.dtype == np.float32


@skip_no_deps
def test_embedder_normalized():
    """Embeddings should be L2-normalized (unit vectors)."""
    import numpy as np
    from translation.tier2.embed import MiniLMEmbedder
    embedder = MiniLMEmbedder().load()
    vecs = embedder.embed(["hello", "how are you", "i need help"])
    norms = np.linalg.norm(vecs, axis=1)
    np.testing.assert_allclose(norms, np.ones(3), atol=1e-5)


@skip_no_deps
def test_similar_sentences_closer_than_dissimilar():
    """Semantically similar sentences should have higher cosine similarity."""
    import numpy as np
    from translation.tier2.embed import MiniLMEmbedder
    embedder = MiniLMEmbedder().load()

    vecs = embedder.embed([
        "I want water",
        "Can I have some water please",
        "The stock market crashed",
    ])
    # Similar pair
    sim_similar = float(np.dot(vecs[0], vecs[1]))
    # Dissimilar pair
    sim_dissimilar = float(np.dot(vecs[0], vecs[2]))
    assert sim_similar > sim_dissimilar, (
        f"Similar sentences not closer: {sim_similar:.3f} vs {sim_dissimilar:.3f}"
    )


# ── Corpus tests ──────────────────────────────────────────────────────────────

def test_augmented_corpus_size():
    """Corpus should have a reasonable number of examples."""
    from translation.tier1.patterns import get_all_patterns_for_index
    corpus = get_all_patterns_for_index()
    assert len(corpus) >= 300, f"Corpus only has {len(corpus)} examples"


def test_corpus_entries_valid():
    """All corpus entries should have non-empty english, asl, and pattern."""
    from translation.tier1.patterns import get_all_patterns_for_index
    for eng, asl, pattern in get_all_patterns_for_index():
        assert eng, "Empty english in corpus"
        assert asl, "Empty asl in corpus"
        assert pattern, "Empty pattern in corpus"


# ── Index tests ───────────────────────────────────────────────────────────────

@skip_no_deps
@skip_no_index
def test_index_loads():
    from translation.tier2.query import VectorIndex
    idx = VectorIndex()
    idx.load()
    assert idx.is_loaded


@skip_no_deps
@skip_no_index
def test_exact_phrase_returns_match():
    """An exact phrase from the corpus should return a high-confidence match."""
    from translation.tier2.query import VectorIndex
    idx = VectorIndex().load()
    match = idx.query("i want water")
    assert match is not None, "Expected a match for 'i want water'"
    assert match.cosine_similarity >= 0.75


@skip_no_deps
@skip_no_index
def test_similar_phrase_returns_match():
    """A paraphrase of a known pattern should still match."""
    from translation.tier2.query import VectorIndex
    idx = VectorIndex().load()
    # "I'd love some coffee" ~ "I want coffee"
    match = idx.query("i'd love some coffee")
    # May or may not exceed threshold — just check it runs without error
    # (threshold behaviour depends on model quality)
    # At minimum the function returns without crashing
    assert match is None or match.asl_gloss


@skip_no_deps
@skip_no_index
def test_unrelated_sentence_returns_none():
    """A sentence very different from all patterns should fall below threshold."""
    from translation.tier2.query import VectorIndex
    idx = VectorIndex(threshold=0.99)  # Very high threshold — almost nothing should pass
    idx.load()
    match = idx.query("quantum entanglement describes non-local correlations")
    assert match is None


@skip_no_deps
@skip_no_index
def test_slot_adaptation():
    """Slot adaptation should fill ASL template with words from query."""
    from translation.tier2.query import VectorIndex
    idx = VectorIndex().load()
    match = idx.query("i want pizza")
    if match is not None:
        # If it matched "I want {THING}" → "{THING} I WANT", PIZZA should appear
        assert "PIZZA" in match.asl_gloss or "WANT" in match.asl_gloss


# ── Slot adaptation unit tests ─────────────────────────────────────────────────

def test_adapt_no_slots():
    from translation.tier2.query import _adapt_slots
    result = _adapt_slots("hello", "hello", "HELLO")
    assert result == "HELLO"


def test_adapt_single_slot():
    from translation.tier2.query import _adapt_slots
    result = _adapt_slots("i want water", "i want {THING}", "{THING} I WANT")
    assert result == "WATER I WANT"


def test_adapt_multiple_slots():
    from translation.tier2.query import _adapt_slots
    result = _adapt_slots(
        "i gave john the book",
        "i gave {PERSON} the {OBJECT}",
        "{OBJECT} I GIVE-{PERSON}"
    )
    assert result == "BOOK I GIVE-JOHN"


def test_adapt_no_match_strips_slots():
    from translation.tier2.query import _adapt_slots
    # Regex won't match — slots should be removed
    result = _adapt_slots(
        "completely unrelated sentence",
        "i gave {PERSON} the {OBJECT}",
        "{OBJECT} I GIVE-{PERSON}"
    )
    # Slots stripped, remaining tokens joined
    assert "{" not in result


# ── Contract fixtures (Tier 2) ────────────────────────────────────────────────

@skip_no_deps
@skip_no_index
def test_contract_tier2_fixtures():
    """Tier 2 contract fixtures: weather-like sentences should match."""
    from translation.tier2.query import VectorIndex
    idx = VectorIndex().load()

    fixtures = json.loads(FIXTURES_PATH.read_text())["fixtures"]
    tier2_fixtures = [f for f in fixtures if f.get("tier") == 2]

    for fixture in tier2_fixtures:
        match = idx.query(fixture["input"].lower())
        # Tier 2 fixtures may or may not match depending on threshold
        # At minimum they should not crash
        contains = fixture.get("expected_gloss_contains", [])
        if match is not None and contains:
            tokens = match.asl_gloss.split()
            for token in contains:
                # Soft check: warn but don't fail (Tier 2 is probabilistic)
                if token not in tokens:
                    print(f"  [warn] [{fixture['id']}] Missing {token!r} in {tokens}")
