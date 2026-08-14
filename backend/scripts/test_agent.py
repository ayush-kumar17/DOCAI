"""
Manual test script for the full agent pipeline.
Run after uploading at least one document.

Usage:
    cd backend
    python scripts/test_agent.py
"""

import asyncio
from services.agent.rag_agent import RAGAgent


async def main():
    agent = RAGAgent()

    test_queries = [
        ("What are the main findings?", "qa"),
        ("Summarize the key points", "summarize"),
        ("List all dates mentioned", "extract"),
    ]

    for query, expected_intent in test_queries:
        print(f"\n{'─'*60}")
        print(f"Query:    {query}")
        print(f"Expected: {expected_intent}")

        result = await agent.run(
            query    = query,
            doc_ids  = [],          # search all docs
            owner_id = None,
            history  = [],
        )

        print(f"Intent:     {result['intent']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Chunks:     {result['chunks_used']}")
        print(f"Iterations: {result['iterations']}")
        print(f"\nAnswer preview:")
        print(result["answer"][:400])
        print(f"\nCitations: {len(result['citations'])}")
        for c in result["citations"][:2]:
            print(f"  Page {c['page']}: {c['text_snippet'][:100]}...")


asyncio.run(main())