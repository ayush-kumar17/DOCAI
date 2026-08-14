"""
File utilities — used by the upload route and document processor.
"""

import uuid
import aiofiles
from pathlib import Path
from typing import Tuple
from config import settings
from utils.exceptions import UnsupportedFileType, FileTooLarge

# Map MIME type → our internal file_type string
MIME_TO_TYPE = {
    "application/pdf":                                                               "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":      "docx",
    "application/msword":                                                            "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation":    "pptx",
    "application/vnd.ms-powerpoint":                                                 "pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":            "xlsx",
    "application/vnd.ms-excel":                                                      "xlsx",
    "text/plain":                                                                    "txt",
    "text/csv":                                                                      "csv",
    "text/markdown":                                                                 "md",
    "image/png":                                                                     "png",
    "image/jpeg":                                                                    "jpg",
    "image/jpg":                                                                     "jpg",
    "image/webp":                                                                    "webp",
    "image/tiff":                                                                    "tiff",
}

ALLOWED_EXTENSIONS = set(MIME_TO_TYPE.values())


def resolve_file_type(content_type: str, filename: str) -> str:
    """
    Determine file type from MIME or extension.
    Raises UnsupportedFileType if neither matches.
    """
    # Try MIME first
    file_type = MIME_TO_TYPE.get(content_type.split(";")[0].strip().lower())

    # Fall back to extension
    if not file_type and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ALLOWED_EXTENSIONS:
            file_type = ext

    if not file_type:
        raise UnsupportedFileType(content_type)

    return file_type


def validate_file_size(size_bytes: int):
    """Raise FileTooLarge if file exceeds configured limit."""
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise FileTooLarge(settings.MAX_FILE_SIZE_MB)


def generate_save_path(file_type: str) -> Tuple[str, Path]:
    """
    Generate a unique file ID and save path.
    Returns (doc_id, full_path).
    """
    doc_id    = str(uuid.uuid4())
    save_name = f"{doc_id}.{file_type}"
    save_path = Path(settings.UPLOAD_DIR) / save_name
    save_path.parent.mkdir(parents=True, exist_ok=True)
    return doc_id, save_path


async def save_upload(file_bytes: bytes, save_path: Path):
    """Write uploaded file bytes to disk asynchronously."""
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(file_bytes)


def delete_file(save_path: Path):
    """Delete a file if it exists. Silent if missing."""
    try:
        if save_path.exists():
            save_path.unlink()
    except Exception:
        pass