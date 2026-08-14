"""
Cross-Encoder Reranker

Why do we need this if we already have vector search + BM25?

Vector search uses bi-encoders:
  - Query  → vector
  - Chunk  → vector
  - Score  = dot product of two vectors
  - Fast but less accurate (encoded separately)

Cross-encoder sees BOTH query and chunk together:
  - Input:  [query] [SEP] [chunk text]
  - Output: relevance score 0-1
  - Much more accurate but slower

Strategy:
  - Use fast bi-encoder to get top 20 candidates
  - Use accurate cross-encoder to re-score those 20
  - Return top 5

This gives us the speed of bi-encoders + accuracy of cross-encoders.
"""

import asyncio
from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from config import settings

logger = get_logger(__name__)

# Global cached reranker model
_reranker = None


def get_reranker():
    """Load cross-encoder once, cache for process lifetime."""
    global _reranker

    if _reranker is None:
        from sentence_transformers import CrossEncoder

        logger.info(f"Loading reranker: {settings.RERANKER_MODEL}")

        _reranker = CrossEncoder(
            settings.RERANKER_MODEL,
            device="cpu",      # <-- IMPORTANT
        )

        logger.info("Reranker loaded on CPU")

    return _reranker


class Reranker:
    """
    Reranks a list of chunks using a cross-encoder model.

    Usage:
        reranker = Reranker()
        top5 = await reranker.rerank(query, chunks, top_k=5)
    """

    async def rerank(
        self,
        query:      str,
        candidates: List[Dict[str, Any]],
        top_k:      int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates using the cross-encoder.

        Args:
            query:      original user query
            candidates: merged results from dense + BM25
            top_k:      how many to return after reranking

        Returns:
            top_k chunks sorted by rerank_score, each with:
            - rerank_score: raw cross-encoder score
            - confidence:   normalized 0-1 score (for citations)
        """
        if not candidates:
            return []

        # Only rerank up to 30 candidates for speed
        # If more, take the top 30 by RRF score first
        candidates = candidates[:30]

        if len(candidates) == 1:
            return [{
                **candidates[0],
                "rerank_score": 1.0,
                "confidence":   1.0,
            }]

        # Run in thread pool (cross-encoder is CPU-bound)
        reranked = await asyncio.to_thread(
            self._rerank_sync, query, candidates, top_k
        )

        return reranked

    def _rerank_sync(
        self,
        query:      str,
        candidates: List[Dict[str, Any]],
        top_k:      int,
    ) -> List[Dict[str, Any]]:
        """Synchronous reranking — called via asyncio.to_thread."""
        reranker = get_reranker()

        # Build (query, chunk_text) pairs
        pairs = [(query, c["text"]) for c in candidates]

        # Cross-encoder scores all pairs
        scores = reranker.predict(pairs)

        # Attach scores to chunks
        for chunk, score in zip(candidates, scores):
            chunk["rerank_score"] = float(score)
            chunk["confidence"]   = self._sigmoid(float(score))

        # Sort by rerank score descending
        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Log top result for debugging
        if candidates:
            logger.info(
                "Reranking complete",
                top_score   = round(candidates[0]["rerank_score"], 3),
                top_confidence = round(candidates[0]["confidence"], 3),
                total_candidates = len(candidates),
            )

        return candidates[:top_k]

    def _sigmoid(self, x: float) -> float:
        """
        Convert raw cross-encoder score to 0-1 confidence.
        Cross-encoder scores can be any real number.
        Sigmoid maps them to (0, 1).
        """
        import math
        return round(1 / (1 + math.exp(-x)), 3)