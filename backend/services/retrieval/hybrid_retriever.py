"""
Hybrid Retriever — the main entry point for all retrieval.

Orchestrates:
  1. Dense (vector) search via Qdrant
  2. BM25 keyword search over dense candidates
  3. RRF fusion of both result sets
  4. Cross-encoder reranking of merged results
"""

from typing import List, Dict, Any, Optional

from services.retrieval.vector_store import VectorStore
from services.retrieval.bm25_retriever import BM25Retriever
from services.retrieval.reranker import Reranker
from services.retrieval.rrf import reciprocal_rank_fusion
from services.embedding.embedder import Embedder
from utils.logger import get_logger

logger = get_logger(__name__)

# Number of candidates
DENSE_TOP_K = 20
BM25_TOP_K = 20

# Final number returned
DEFAULT_TOP_K = 5


class HybridRetriever:
    """
    Full hybrid retrieval pipeline.
    """

    def __init__(self):
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.bm25 = BM25Retriever()
        self.reranker = Reranker()

    async def retrieve(
        self,
        query: str,
        doc_ids: Optional[List[str]] = None,
        owner_id: Optional[str] = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> List[Dict[str, Any]]:

        logger.info(
            "Starting hybrid retrieval",
            query=query[:80],
            doc_ids=doc_ids,
            owner_id=owner_id,
            top_k=top_k,
        )

        # ----------------------------------------------------
        # Step 1: Embed query
        # ----------------------------------------------------
        query_vector = await self.embedder.embed_query(query)

        # ====================================================
        # DEBUG
        # ====================================================
        print("\n" + "=" * 70)
        print("HYBRID RETRIEVER DEBUG")
        print("=" * 70)
        print("Query    :", query)
        print("Owner ID :", owner_id)
        print("Doc IDs  :", doc_ids)
        print("=" * 70 + "\n")

        # ----------------------------------------------------
        # Step 2: Dense Search
        # ----------------------------------------------------
        dense_results = await self.vector_store.search(
            vector=query_vector,
            doc_ids=doc_ids,
            owner_id=owner_id,
            limit=DENSE_TOP_K,
        )

        print(f"\nDense Search Returned: {len(dense_results)} results")

        if dense_results:
            print("\nTop 3 Dense Results:")
            for i, r in enumerate(dense_results[:3], start=1):
                print(f"{i}.")
                print("   doc_id :", r.get("doc_id"))
                print("   page   :", r.get("page"))
                print("   score  :", r.get("score"))
                print("   text   :", r.get("text", "")[:100])
                print()

        logger.info(f"Dense search returned {len(dense_results)} results")

        if not dense_results:
            logger.warning("Dense search returned no results")
            return []

        # ----------------------------------------------------
        # Step 3: BM25
        # ----------------------------------------------------
        bm25_results = self.bm25.search(
            query=query,
            candidates=dense_results,
            top_k=BM25_TOP_K,
        )

        logger.info(f"BM25 search returned {len(bm25_results)} results")

        # ----------------------------------------------------
        # Step 4: RRF
        # ----------------------------------------------------
        merged = reciprocal_rank_fusion(
            dense_results=dense_results,
            bm25_results=bm25_results,
        )

        logger.info(f"RRF fusion produced {len(merged)} unique chunks")

        # ----------------------------------------------------
        # Step 5: Cross Encoder
        # ----------------------------------------------------
        reranked = await self.reranker.rerank(
            query=query,
            candidates=merged,
            top_k=top_k,
        )

        logger.info(
            "Retrieval complete",
            returned=len(reranked),
            top_confidence=reranked[0]["confidence"] if reranked else 0,
        )

        return reranked

    async def retrieve_for_comparison(
        self,
        query: str,
        doc_ids: List[str],
        top_k_per_doc: int = 3,
    ) -> Dict[str, List[Dict[str, Any]]]:

        results = {}

        for doc_id in doc_ids:
            chunks = await self.retrieve(
                query=query,
                doc_ids=[doc_id],
                top_k=top_k_per_doc,
            )
            results[doc_id] = chunks

        return results