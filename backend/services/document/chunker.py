"""
Semantic Chunker

Splits extracted pages into retrieval-optimized chunks.

Why not just split every 500 tokens?
  Fixed splits break sentences mid-thought. A chunk like
  "...the patient showed signs of" is useless without context.

Our strategy:
  1. Try to split on paragraph boundaries first
  2. Fall back to sentence boundaries
  3. Last resort: character split
  4. Add overlap between chunks so context isn't lost at edges
  5. Never split inside a [TABLE] block
"""

import re
from typing import List, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

# Target chunk size in words (not tokens — simpler, close enough)
CHUNK_SIZE = 400

# How many words to repeat at the start of the next chunk
# This gives the LLM context about what came before
OVERLAP = 50


class SemanticChunker:

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        overlap:    int = OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.overlap    = overlap

    def chunk(
        self,
        pages:  List[Dict[str, Any]],
        doc_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Main entry point.

        Input:  pages from any extractor
        Output: list of chunk dicts ready to embed and store
        """
        chunks      = []
        chunk_index = 0

        for page in pages:
            text       = page.get("text", "").strip()
            page_num   = page.get("page_number", 1)
            section    = page.get("section", "")
            has_table  = page.get("has_table", False)

            if not text:
                continue

            # Tables: keep as single chunk, don't split them
            if has_table and "[TABLE]" in text:
                table_chunks = self._split_preserving_tables(text)
            else:
                table_chunks = self._split_text(text)

            for text_chunk in table_chunks:
                text_chunk = text_chunk.strip()
                if not text_chunk:
                    continue

                chunks.append({
                    "chunk_index": chunk_index,
                    "text":        text_chunk,
                    "page_number": page_num,
                    "section":     section,
                    "has_table":   "[TABLE]" in text_chunk,
                    "has_image":   page.get("has_image", False),
                    "token_count": len(text_chunk.split()),
                })
                chunk_index += 1

        logger.info(
            "Chunking complete",
            doc_id=doc_id,
            pages=len(pages),
            chunks=len(chunks),
        )
        return chunks

    # ──────────────────────────────────────────
    # Internal splitting methods
    # ──────────────────────────────────────────

    def _split_text(self, text: str) -> List[str]:
        """
        Split plain text into chunks with overlap.
        Tries paragraph → sentence → word boundaries in that order.
        """
        word_count = len(text.split())

        # Short enough to be one chunk
        if word_count <= self.chunk_size:
            return [text]

        # Try paragraph split
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        if len(paragraphs) > 1:
            return self._merge_into_chunks(paragraphs)

        # Try sentence split
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        if len(sentences) > 1:
            return self._merge_into_chunks(sentences)

        # Hard word split as last resort
        return self._hard_split(text)

    def _merge_into_chunks(self, pieces: List[str]) -> List[str]:
        """
        Greedily merge pieces into chunks of target size.
        Adds overlap between chunks.
        """
        chunks      = []
        current     = []
        current_len = 0

        for piece in pieces:
            piece_len = len(piece.split())

            # Current chunk is full — flush it
            if current_len + piece_len > self.chunk_size and current:
                chunk_text = " ".join(current)
                chunks.append(chunk_text)

                # Start next chunk with overlap from end of current
                overlap_words = " ".join(current).split()[-self.overlap:]
                current       = [" ".join(overlap_words)] if overlap_words else []
                current_len   = len(overlap_words)

            current.append(piece)
            current_len += piece_len

        # Flush remaining
        if current:
            chunks.append(" ".join(current))

        return chunks

    def _hard_split(self, text: str) -> List[str]:
        """Word-level split when no sentence boundaries found."""
        words   = text.split()
        chunks  = []
        step    = self.chunk_size - self.overlap

        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + self.chunk_size])
            chunks.append(chunk)

        return chunks

    def _split_preserving_tables(self, text: str) -> List[str]:
        """
        Split text while keeping TABLE blocks intact.
        Non-table parts go through normal splitting.
        Table parts become individual chunks.
        """
        # Split on table markers, keeping the markers
        parts  = re.split(r"(\[TABLE\].*?\[/TABLE\])", text, flags=re.DOTALL)
        result = []

        for part in parts:
            if not part.strip():
                continue
            if part.startswith("[TABLE]"):
                result.append(part.strip())
            else:
                result.extend(self._split_text(part))

        return result