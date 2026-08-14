"""
Embedding Service

Converts text chunks into dense vectors using BGE-large-en-v1.5.

Why BGE-large?
  - Top of the MTEB retrieval benchmark
  - Open source, runs locally, no API costs
  - 1024 dimensions — good balance of quality vs storage

The model is loaded once per worker process and cached.
Loading takes ~10 seconds and ~1.5GB RAM.
"""

import asyncio
from typing import List
from utils.logger import get_logger
from config import settings

logger = get_logger(__name__)

# Batch size for encoding
# Higher = faster but more RAM
# 64 is safe for 16GB RAM machines
BATCH_SIZE = 64

# Global cached model
_model = None


def get_model():
    """Load model once, cache for process lifetime."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded")
    return _model


class Embedder:
    """
    Async-safe embedding service.

    All heavy computation runs in a thread pool via asyncio.to_thread()
    so it doesn't block the FastAPI event loop.
    """

    def get_dimension(self) -> int:
        """Return vector dimension. Used when creating Qdrant collection."""
        return settings.EMBEDDING_DIMENSION

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts.
        Returns a list of vectors (each vector is a list of floats).

        Usage:
            embedder  = Embedder()
            vectors   = await embedder.embed_batch(["hello world", "foo bar"])
            # vectors[0] is a list of 1024 floats
        """
        if not texts:
            return []

        # Run in thread pool — SentenceTransformer is not async
        vectors = await asyncio.to_thread(self._encode, texts)
        return vectors

    async def embed_query(self, query: str) -> List[float]:
        """
        Embed a single search query.

        BGE models work better with a prefix for queries.
        Document chunks are embedded WITHOUT the prefix.
        Queries are embedded WITH the prefix.
        This asymmetry improves retrieval quality.
        """
        prefixed = f"Represent this sentence for searching relevant passages: {query}"
        results  = await self.embed_batch([prefixed])
        return results[0]

    def _encode(self, texts: List[str]) -> List[List[float]]:
        """
        Synchronous encoding — called via to_thread().
        normalize_embeddings=True means we can use dot product
        instead of cosine similarity (faster, same result).
        """
        model = get_model()

        embeddings = model.encode(
            texts,
            batch_size          = BATCH_SIZE,
            normalize_embeddings= True,
            show_progress_bar   = False,
            convert_to_numpy    = True,
        )

        return embeddings.tolist()