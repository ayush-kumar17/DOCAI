"""
OCR Service — extracts text from scanned PDFs and images.

Uses EasyOCR which works offline, no API key needed.
The reader is loaded once and cached (it's heavy — ~200MB model).

When is OCR triggered?
  - Image files (png, jpg, webp, tiff) — always
  - PDF pages where extracted text is less than 50 characters
    (that means the page is a scanned image, not real text)
"""

import asyncio
from typing import Optional
import numpy as np
from PIL import Image
import io

from utils.logger import get_logger

logger = get_logger(__name__)

# Global cached reader — loaded once per worker process
_reader = None


def get_reader():
    """
    Load EasyOCR reader. Heavy operation — only done once.
    gpu=False means it works on any machine without a GPU.
    Add "ch_sim" to the list for Chinese support, etc.
    """
    global _reader
    if _reader is None:
        logger.info("Loading EasyOCR model — this takes ~30 seconds on first load")
        import easyocr
        _reader = easyocr.Reader(["en"], gpu=False)
        logger.info("EasyOCR model loaded")
    return _reader


def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """
    Run OCR on raw image bytes.
    Returns extracted text as a single string.
    """
    reader  = get_reader()
    results = reader.readtext(image_bytes, detail=0, paragraph=True)
    return " ".join(results).strip()


def extract_text_from_image_file(file_path: str) -> str:
    """
    Run OCR on an image file (png, jpg, webp, tiff).
    """
    reader  = get_reader()
    results = reader.readtext(file_path, detail=0, paragraph=True)
    return " ".join(results).strip()


async def ocr_image_bytes_async(image_bytes: bytes) -> str:
    """Async wrapper — runs OCR in thread pool so it doesn't block FastAPI."""
    return await asyncio.to_thread(extract_text_from_image_bytes, image_bytes)


async def ocr_image_file_async(file_path: str) -> str:
    """Async wrapper for file-based OCR."""
    return await asyncio.to_thread(extract_text_from_image_file, file_path)