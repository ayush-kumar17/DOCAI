"""
Unit tests for agent nodes.
Mock the LLM and retriever so tests run without API keys.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ── Test router node ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_router_classifies_qa():
    mock_response = MagicMock()
    mock_response.content = "qa"

    with patch("services.agent.nodes.get_llm") as mock_llm:
        mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

        from services.agent.nodes import router_node

        state = {
            "query":   "What is the main finding?",
            "doc_ids": ["doc1"],
        }

        result = await router_node(state)

        assert result["intent"] == "qa"
        assert result["retrieval_queries"] == ["What is the main finding?"]
        assert result["iteration"] == 0


@pytest.mark.asyncio
async def test_router_defaults_on_unknown_intent():
    mock_response = MagicMock()
    mock_response.content = "unknown_intent_xyz"

    with patch("services.agent.nodes.get_llm") as mock_llm:
        mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

        from services.agent.nodes import router_node

        state = {"query": "something", "doc_ids": []}
        result = await router_node(state)

        assert result["intent"] == "qa"


@pytest.mark.asyncio
async def test_router_compare_creates_multiple_queries():
    mock_response = MagicMock()
    mock_response.content = "compare"

    with patch("services.agent.nodes.get_llm") as mock_llm:
        mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

        from services.agent.nodes import router_node

        state = {
            "query":   "Compare these reports",
            "doc_ids": ["doc1", "doc2"],
        }

        result = await router_node(state)

        assert result["intent"] == "compare"
        assert len(result["retrieval_queries"]) == 2


# ── Test should_refine ────────────────────────────────────────────────────────

def test_should_refine_when_low_confidence():
    from services.agent.nodes import should_refine

    state = {"confidence": 0.2, "iteration": 0}
    assert should_refine(state) == "refine"


def test_should_not_refine_when_high_confidence():
    from services.agent.nodes import should_refine

    state = {"confidence": 0.8, "iteration": 0}
    assert should_refine(state) == "done"


def test_should_not_refine_after_max_iterations():
    from services.agent.nodes import should_refine

    # Even with low confidence, stop after 2 iterations
    state = {"confidence": 0.1, "iteration": 2}
    assert should_refine(state) == "done"


# ── Test helper functions ─────────────────────────────────────────────────────

def test_extract_confidence():
    from services.agent.nodes import _extract_confidence

    text = "The answer is X.\n\nCONFIDENCE: 0.85"
    assert _extract_confidence(text) == 0.85


def test_extract_confidence_default_when_missing():
    from services.agent.nodes import _extract_confidence

    text = "The answer is X. No confidence score here."
    assert _extract_confidence(text) == 0.7


def test_extract_confidence_clamped_to_one():
    from services.agent.nodes import _extract_confidence

    text = "CONFIDENCE: 1.5"
    assert _extract_confidence(text) == 1.0


def test_build_citations():
    from services.agent.nodes import _build_citations

    chunks = [
        {
            "doc_id": "abc123",
            "page": 5,
            "section": "Introduction",
            "confidence": 0.92,
            "text": "This is the chunk text " * 20,
            "rerank_score": 3.2,
        }
    ]

    citations = _build_citations(chunks)

    assert len(citations) == 1
    assert citations[0]["doc_id"] == "abc123"
    assert citations[0]["page"] == 5
    assert len(citations[0]["text_snippet"]) <= 300