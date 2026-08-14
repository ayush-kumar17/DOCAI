"""
Reciprocal Rank Fusion (RRF)

Merges two ranked lists (dense + BM25) into one.

The problem:
  Dense search returns chunks ranked [A, B, C, D, ...]
  BM25 returns chunks ranked [C, A, E, B, ...]
  Both are good signals. How do we combine them?

Naive approach: average the scores
  Problem: scores from different systems aren't comparable
  Dense scores are cosine similarities (0-1)
  BM25 scores are term frequencies (0-∞)

RRF approach: use rank position, not score value
  Score = Σ 1/(k + rank)    where k=60 (smoothing constant)

  If chunk A is rank 1 in dense and rank 2 in BM25:
    RRF score = 1/(60+1) + 1/(60+2) = 0.0164 + 0.0161 = 0.0325

  If chunk C is rank 3 in dense and rank 1 in BM25:
    RRF score = 1/(60+3) + 1/(60+1) = 0.0159 + 0.0164 = 0.0323

  They're almost equal — which makes sense, both are highly relevant.

Why k=60?
  Empirically shown to work well across many tasks.
  Higher k = rank position matters less.
  Lower k = position matters more.
"""

from typing import List, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

# Standard RRF smoothing constant
RRF_K = 60


def reciprocal_rank_fusion(
    dense_results:  List[Dict[str, Any]],
    bm25_results:   List[Dict[str, Any]],
    k:              int = RRF_K,
) -> List[Dict[str, Any]]:
    """
    Merge two ranked lists using RRF.

    Args:
        dense_results:  chunks from vector search, in rank order
        bm25_results:   chunks from BM25, in rank order
        k:              smoothing constant (default 60)

    Returns:
        merged list sorted by RRF score descending, deduplicated
    """
    # Track: chunk_id → rrf_score
    scores: Dict[str, float] = {}

    # Track: chunk_id → chunk data
    chunks: Dict[str, Dict]  = {}

    # Score from dense results
    for rank, chunk in enumerate(dense_results):
        chunk_id = chunk["id"]
        rrf_score = 1.0 / (k + rank + 1)

        scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_score
        chunks[chunk_id] = chunk

    # Score from BM25 results
    for rank, chunk in enumerate(bm25_results):
        chunk_id  = chunk["id"]
        rrf_score = 1.0 / (k + rank + 1)

        scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_score

        # BM25 may have chunks not in dense — add them
        if chunk_id not in chunks:
            chunks[chunk_id] = chunk

    # Sort all unique chunks by RRF score
    merged = sorted(
        chunks.values(),
        key     = lambda c: scores[c["id"]],
        reverse = True,
    )

    # Attach RRF score for debugging
    for chunk in merged:
        chunk["rrf_score"] = round(scores[chunk["id"]], 6)

    logger.info(
        "RRF fusion complete",
        dense_count  = len(dense_results),
        bm25_count   = len(bm25_results),
        merged_count = len(merged),
    )

    return merged