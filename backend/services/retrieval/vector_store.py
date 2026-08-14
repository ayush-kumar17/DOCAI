"""
Qdrant Vector Store

Wraps the Qdrant client to provide simple upsert/search/delete operations.

Collection structure:
  - One collection called "documents"
  - Each point represents one chunk
  - Payload fields: doc_id, chunk_index, text, page, section, owner_id
  - Filtered by doc_id or owner_id on search
"""

import asyncio
from typing import List, Dict, Any, Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    ScoredPoint,
)
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

COLLECTION  = settings.QDRANT_COLLECTION
VECTOR_SIZE = settings.EMBEDDING_DIMENSION


class VectorStore:
    """
    Async Qdrant client wrapper.

    Usage:
        vs = VectorStore()
        await vs.upsert(points)
        results = await vs.search(vector, doc_ids=["abc", "def"])
    """

    def __init__(self):
        self.client = AsyncQdrantClient(url=settings.QDRANT_URL)

    async def ensure_collection(self):
        """
        Create the collection if it doesn't exist.
        Safe to call multiple times — idempotent.
        """
        existing = await self.client.get_collections()
        names    = [c.name for c in existing.collections]

        if COLLECTION not in names:
            await self.client.create_collection(
                collection_name = COLLECTION,
                vectors_config  = VectorParams(
                    size     = VECTOR_SIZE,
                    distance = Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {COLLECTION}")
        else:
            logger.info(f"Qdrant collection exists: {COLLECTION}")

    async def upsert(self, points: List[Dict[str, Any]]):
        """
        Insert or update vectors.

        Each point must be:
        {
            "id":      "uuid-string",
            "vector":  [0.1, 0.2, ...],   # 1024 floats
            "payload": {
                "doc_id":      "...",
                "owner_id":    "...",
                "chunk_index": 0,
                "text":        "...",
                "page":        1,
                "section":     "...",
            }
        }
        """
        await self.ensure_collection()

        qdrant_points = [
            PointStruct(
                id      = p["id"],
                vector  = p["vector"],
                payload = p["payload"],
            )
            for p in points
        ]

        # Upsert in batches of 100 to avoid timeouts
        batch_size = 100
        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i : i + batch_size]
            await self.client.upsert(
                collection_name = COLLECTION,
                points          = batch,
            )

        logger.info(f"Upserted {len(points)} vectors")

    async def search(
        self,
        vector:   List[float],
        doc_ids:  Optional[List[str]] = None,
        owner_id: Optional[str] = None,
        limit:    int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search.

        doc_ids:  restrict to specific documents
        owner_id: restrict to a specific user's documents
        limit:    how many results to return
        """
        # Build filter
        conditions = []

        if doc_ids:
            conditions.append(
                FieldCondition(
                    key   = "doc_id",
                    match = MatchAny(any=doc_ids),
                )
            )

        if owner_id:
            conditions.append(
                FieldCondition(
                    key   = "owner_id",
                    match = MatchValue(value=owner_id),
                )
            )

        query_filter = Filter(must=conditions) if conditions else None

        results: List[ScoredPoint] = await self.client.search(
            collection_name = COLLECTION,
            query_vector    = vector,
            query_filter    = query_filter,
            limit           = limit,
            with_payload    = True,
        )

        return [
            {
                "id":      str(r.id),
                "score":   r.score,
                "text":    r.payload.get("text", ""),
                "doc_id":  r.payload.get("doc_id"),
                "page":    r.payload.get("page"),
                "section": r.payload.get("section", ""),
            }
            for r in results
        ]

    async def delete_by_doc(self, doc_id: str):
        """
        Remove all vectors belonging to a document.
        Called when a document is deleted.
        """
        from qdrant_client.models import FilterSelector

        await self.client.delete(
            collection_name  = COLLECTION,
            points_selector  = FilterSelector(
                filter = Filter(
                    must = [
                        FieldCondition(
                            key   = "doc_id",
                            match = MatchValue(value=doc_id),
                        )
                    ]
                )
            ),
        )
        logger.info(f"Deleted vectors for doc: {doc_id}")