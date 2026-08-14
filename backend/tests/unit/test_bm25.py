"""Tests for BM25 retriever."""
import pytest
from services.retrieval.bm25_retriever import BM25Retriever


@pytest.fixture
def retriever():
    return BM25Retriever()


def make_chunk(id: str, text: str) -> dict:
    return {"id": id, "text": text, "doc_id": "doc1", "page": 1, "section": "", "score": 0.9}


def test_exact_match_ranks_first(retriever):
    candidates = [
        make_chunk("A", "The quick brown fox jumps over the lazy dog"),
        make_chunk("B", "Machine learning is a subset of artificial intelligence"),
        make_chunk("C", "neural networks and deep learning models"),
    ]
    results = retriever.search("machine learning artificial intelligence", candidates)
    assert results[0]["id"] == "B"


def test_bm25_score_attached(retriever):
    candidates = [
        make_chunk("A", "hello world"),
        make_chunk("B", "goodbye world"),
    ]
    results = retriever.search("hello", candidates)
    for r in results:
        assert "bm25_score" in r


def test_empty_candidates_returns_empty(retriever):
    results = retriever.search("any query", [])
    assert results == []


def test_top_k_respected(retriever):
    candidates = [make_chunk(str(i), f"text about topic {i}") for i in range(10)]
    results = retriever.search("topic", candidates, top_k=3)
    assert len(results) <= 3