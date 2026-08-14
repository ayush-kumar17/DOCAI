"""Tests for Reciprocal Rank Fusion."""
import pytest
from services.retrieval.rrf import reciprocal_rank_fusion


def make_chunk(id: str, text: str = "sample text") -> dict:
    return {"id": id, "text": text, "doc_id": "doc1", "page": 1, "section": "", "score": 0.9}


def test_rrf_deduplicates():
    """Same chunk in both lists should appear once in output."""
    dense = [make_chunk("A"), make_chunk("B"), make_chunk("C")]
    bm25  = [make_chunk("C"), make_chunk("A"), make_chunk("D")]

    merged = reciprocal_rank_fusion(dense, bm25)
    ids    = [c["id"] for c in merged]

    # No duplicates
    assert len(ids) == len(set(ids))

    # All 4 unique chunks present
    assert set(ids) == {"A", "B", "C", "D"}


def test_rrf_score_higher_for_top_ranked():
    """Chunk ranked first in both lists should have highest RRF score."""
    dense = [make_chunk("A"), make_chunk("B"), make_chunk("C")]
    bm25  = [make_chunk("A"), make_chunk("C"), make_chunk("B")]

    merged = reciprocal_rank_fusion(dense, bm25)

    # A is rank 1 in both — should be first
    assert merged[0]["id"] == "A"


def test_rrf_returns_all_unique_chunks():
    """Chunks only in one list should still appear in output."""
    dense = [make_chunk("A"), make_chunk("B")]
    bm25  = [make_chunk("C"), make_chunk("D")]

    merged = reciprocal_rank_fusion(dense, bm25)
    ids    = [c["id"] for c in merged]

    assert "A" in ids
    assert "B" in ids
    assert "C" in ids
    assert "D" in ids


def test_rrf_score_attached():
    """Every merged chunk should have rrf_score attached."""
    dense  = [make_chunk("A"), make_chunk("B")]
    bm25   = [make_chunk("A"), make_chunk("C")]
    merged = reciprocal_rank_fusion(dense, bm25)

    for chunk in merged:
        assert "rrf_score" in chunk
        assert chunk["rrf_score"] > 0


def test_empty_lists_return_empty():
    merged = reciprocal_rank_fusion([], [])
    assert merged == []


def test_one_empty_list():
    dense  = [make_chunk("A"), make_chunk("B")]
    merged = reciprocal_rank_fusion(dense, [])
    assert len(merged) == 2