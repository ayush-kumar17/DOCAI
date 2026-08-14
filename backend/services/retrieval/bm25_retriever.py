"""
BM25 Retrieval

BM25 (Best Match 25) is a classic keyword search algorithm.
It's what search engines used before neural networks.

Why we still need it alongside vector search:
  - Vector search misses exact matches: searching "GPT-4o"
    might return chunks about "language models" instead
  - BM25 finds exact keyword matches reliably
  - Together they cover both meaning AND exact terms

How it works:
  - Score each chunk by how often query words appear in it
  - Adjusted for document length (long docs don't get unfair advantage)
  - TF-IDF style scoring with saturation

We build the BM25 index on the fly from retrieved candidates
rather than pre-building per document. This keeps it simple
and still fast enough for our use case.
"""

from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from utils.logger import get_logger

logger = get_logger(__name__)


class BM25Retriever:
    """
    In-memory BM25 search over a candidate set of chunks.

    We don't pre-index all documents with BM25. Instead:
    1. Dense search gives us top-20 semantic candidates
    2. We build BM25 over just those 20 candidates
    3. BM25 re-scores them by keyword match

    This is fast, simple, and effective.
    """

    def search(
        self,
        query:      str,
        candidates: List[Dict[str, Any]],
        top_k:      int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Run BM25 over a candidate list.

        Args:
            query:      the user's search query
            candidates: chunks from vector search (each has a "text" field)
            top_k:      how many results to return

        Returns:
            same format as input, with bm25_score added, sorted by score
        """
        if not candidates:
            return []

        if len(candidates) == 1:
            return [{**candidates[0], "bm25_score": 1.0}]

        # Tokenize corpus
        # Simple whitespace tokenization — good enough for BM25
        tokenized_corpus = [
            self._tokenize(c["text"]) for c in candidates
        ]
        tokenized_query = self._tokenize(query)

        # Build BM25 index over this small corpus
        bm25   = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(tokenized_query)

        # Attach scores
        scored = [
            {**chunk, "bm25_score": float(score)}
            for chunk, score in zip(candidates, scores)
        ]

        # Sort by BM25 score descending
        scored.sort(key=lambda x: x["bm25_score"], reverse=True)

        return scored[:top_k]

    def search_over_texts(
        self,
        query:  str,
        texts:  List[str],
        top_k:  int = 20,
    ) -> List[int]:
        """
        Search over raw texts, returns indices of top results.
        Used when you have texts but not chunk dicts.
        """
        if not texts:
            return []

        tokenized_corpus = [self._tokenize(t) for t in texts]
        tokenized_query  = self._tokenize(query)

        bm25   = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(tokenized_query)

        # Return indices sorted by score
        indexed = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )

        return [idx for idx, _ in indexed[:top_k]]

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenizer.
        Lowercase + split on whitespace.
        Removes very short tokens (1-2 chars) to reduce noise.
        """
        tokens = text.lower().split()
        return [t for t in tokens if len(t) > 2]