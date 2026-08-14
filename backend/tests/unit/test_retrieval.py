"""
Integration test for hybrid retrieval.
Requires Qdrant running. Skip if not available.

Run with:
  pytest tests/integration/test_retrieval.py -v
"""

import pytest
import asyncio

pytestmark = pytest.mark.asyncio


async def qdrant_available() -> bool:
    """Check if Qdrant is running."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:6333/health", timeout=2.0)
            return r.status_code == 200
    except Exception:
        return False


@pytest.mark.asyncio
async def test_vector_store_upsert_and_search():
    if not await qdrant_available():
        pytest.skip("Qdrant not running")

    from services.retrieval.vector_store import VectorStore

    vs = VectorStore()

    # Upsert a test point
    test_point = {
        "id":     "test-point-001",
        "vector": [0.1] * 1024,      # fake 1024-dim vector
        "payload": {
            "doc_id":      "test-doc",
            "owner_id":    "test-user",
            "chunk_index": 0,
            "text":        "This is a test chunk about machine learning",
            "page":        1,
            "section":     "Introduction",
            "has_table":   False,
        },
    }

    await vs.upsert([test_point])

    # Search with same vector — should return itself
    results = await vs.search(
        vector  = [0.1] * 1024,
        doc_ids = ["test-doc"],
        limit   = 5,
    )

    assert len(results) >= 1
    assert any(r["doc_id"] == "test-doc" for r in results)

    # Cleanup
    await vs.delete_by_doc("test-doc")