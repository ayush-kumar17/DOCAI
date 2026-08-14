"""
Document Processor — orchestrates the full pipeline.

Pipeline:
  file on disk
      ↓
  extract text (by file type)
      ↓
  clean extracted text
      ↓
  chunk into pieces
      ↓
  embed each chunk → vector
      ↓
  store vectors in Qdrant
      ↓
  return chunk list for DB storage

This is called by the Celery worker, not directly by FastAPI routes.
"""

import asyncio
import re
import uuid
from typing import Dict, Any

from services.document.extractors import extract_document
from services.document.chunker import SemanticChunker
from services.embedding.embedder import Embedder
from services.retrieval.vector_store import VectorStore
from utils.logger import get_logger

logger = get_logger(__name__)


class DocumentProcessor:
    """
    Orchestrates extraction → cleaning → chunking → embedding → storage.
    """

    def __init__(self):
        self.chunker = SemanticChunker()
        self.embedder = Embedder()
        self.vector_store = VectorStore()

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Remove characters that PostgreSQL cannot store and normalize text.
        """
        if not text:
            return ""

        # PostgreSQL cannot store NULL bytes
        text = text.replace("\x00", "")

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace tabs with spaces
        text = text.replace("\t", " ")

        # Remove other control characters except newline
        text = "".join(
            ch for ch in text
            if ch == "\n" or ord(ch) >= 32
        )

        # Collapse multiple spaces
        text = re.sub(r"[ ]{2,}", " ", text)

        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    async def process(
        self,
        file_path: str,
        doc_id: str,
        file_type: str,
        owner_id: str,
    ) -> Dict[str, Any]:

        logger.info(
            "Processing document",
            doc_id=doc_id,
            file_type=file_type,
            file_path=file_path,
        )

        # --------------------------------------------------
        # Step 1: Extract
        # --------------------------------------------------

        pages = await asyncio.to_thread(
            extract_document,
            file_path,
            file_type,
        )

        if not pages:
            raise ValueError(
                "No text could be extracted from document"
            )

        # --------------------------------------------------
        # Step 2: Clean extracted pages
        # --------------------------------------------------

        for page in pages:
            page["text"] = self.clean_text(
                page.get("text", "")
            )

        page_count = max(
            p.get("page_number", 1)
            for p in pages
        )

        logger.info(
            "Extracted %d pages",
            len(pages),
        )

        # --------------------------------------------------
        # Step 3: Chunk
        # --------------------------------------------------

        chunks = self.chunker.chunk(
            pages,
            doc_id=doc_id,
        )

        if not chunks:
            raise ValueError(
                "Document produced no chunks after processing"
            )

        # Clean chunk text again (cheap safety check)
        for chunk in chunks:
            chunk["text"] = self.clean_text(
                chunk.get("text", "")
            )

        logger.info(
            "Created %d chunks",
            len(chunks),
        )

        # --------------------------------------------------
        # Step 4: Embeddings
        # --------------------------------------------------

        texts = [c["text"] for c in chunks]

        embeddings = await self.embedder.embed_batch(texts)

        logger.info(
            "Generated %d embeddings",
            len(embeddings),
        )

        # --------------------------------------------------
        # Step 5: Store vectors
        # --------------------------------------------------

        points = []

        for chunk, embedding in zip(chunks, embeddings):

            vector_id = str(uuid.uuid4())

            chunk["vector_id"] = vector_id

            points.append(
                {
                    "id": vector_id,
                    "vector": embedding,
                    "payload": {
                        "doc_id": doc_id,
                        "owner_id": owner_id,
                        "chunk_index": chunk["chunk_index"],
                        "text": chunk["text"],
                        "page": chunk.get("page_number"),
                        "section": chunk.get("section", ""),
                        "has_table": chunk.get("has_table", False),
                    },
                }
            )

        await self.vector_store.upsert(points)

        logger.info(
            "Stored %d vectors in Qdrant",
            len(points),
        )

        return {
            "chunks": chunks,
            "page_count": page_count,
            "chunk_count": len(chunks),
        }