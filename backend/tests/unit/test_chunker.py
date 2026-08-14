"""Tests for the semantic chunker."""
import pytest
from services.document.chunker import SemanticChunker


@pytest.fixture
def chunker():
    return SemanticChunker(chunk_size=50, overlap=10)


def test_short_text_stays_one_chunk(chunker):
    pages = [{"page_number": 1, "text": "This is a short text.", "section": "", "has_table": False}]
    chunks = chunker.chunk(pages, doc_id="test-doc")
    assert len(chunks) == 1
    assert chunks[0]["text"] == "This is a short text."


def test_long_text_splits_into_multiple(chunker):
    long_text = " ".join([f"word{i}" for i in range(200)])
    pages  = [{"page_number": 1, "text": long_text, "section": "", "has_table": False}]
    chunks = chunker.chunk(pages, doc_id="test-doc")
    assert len(chunks) > 1


def test_table_not_split(chunker):
    table_text = "[TABLE]\ncol1 | col2\nval1 | val2\n[/TABLE]"
    pages  = [{"page_number": 1, "text": table_text, "section": "", "has_table": True}]
    chunks = chunker.chunk(pages, doc_id="test-doc")
    # Table should be kept as one chunk
    table_chunks = [c for c in chunks if "[TABLE]" in c["text"]]
    assert len(table_chunks) == 1


def test_chunk_index_sequential(chunker):
    long_text = " ".join([f"word{i}" for i in range(300)])
    pages  = [{"page_number": 1, "text": long_text, "section": "", "has_table": False}]
    chunks = chunker.chunk(pages, doc_id="test-doc")
    indices = [c["chunk_index"] for c in chunks]
    assert indices == list(range(len(chunks)))


def test_page_number_preserved(chunker):
    pages = [
        {"page_number": 5, "text": "Text on page 5.", "section": "Intro", "has_table": False},
    ]
    chunks = chunker.chunk(pages, doc_id="test-doc")
    assert chunks[0]["page_number"] == 5
    assert chunks[0]["section"] == "Intro"