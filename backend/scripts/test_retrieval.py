# backend/scripts/test_retrieval.py
import asyncio
from services.retrieval.hybrid_retriever import HybridRetriever

async def main():
    retriever = HybridRetriever()

    results = await retriever.retrieve(
        query   = "What are the main conclusions?",
        top_k   = 5,
    )

    for i, chunk in enumerate(results):
        print(f"\n── Chunk {i+1} ──")
        print(f"Page:       {chunk['page']}")
        print(f"Section:    {chunk['section']}")
        print(f"Confidence: {chunk['confidence']}")
        print(f"Text:       {chunk['text'][:200]}...")

asyncio.run(main())