"""
Document API routes.

POST   /api/documents/upload     — upload a file
GET    /api/documents            — list my documents
GET    /api/documents/{doc_id}   — get document details
DELETE /api/documents/{doc_id}   — delete a document
GET    /api/documents/{doc_id}/status — poll processing status
"""

import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database.connection import get_db
from database.models import Document, Chunk
from auth.dependencies import get_current_user
from utils.file_utils import (
    resolve_file_type,
    validate_file_size,
    generate_save_path,
    save_upload,
    delete_file,
)
from utils.exceptions import DocumentNotFound
from celery_app import process_document_task
from utils.logger import get_logger

logger   = get_logger(__name__)
router   = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db:   AsyncSession = Depends(get_db),
    user               = Depends(get_current_user),
):
    """
    Upload a document for processing.

    Returns immediately with doc_id and status=pending.
    Processing happens in background via Celery.
    Poll /api/documents/{doc_id}/status to check progress.
    """
    # Read file into memory
    file_bytes = await file.read()

    # Validate
    file_type  = resolve_file_type(file.content_type or "", file.filename or "")
    validate_file_size(len(file_bytes))

    # Save to disk
    doc_id, save_path = generate_save_path(file_type)
    await save_upload(file_bytes, save_path)

    # Create DB record
    doc = Document(
        id            = uuid.UUID(doc_id),
        owner_id      = user.id,
        filename      = save_path.name,
        original_name = file.filename or "unknown",
        file_type     = file_type,
        file_size     = len(file_bytes),
        status        = "pending",
    )
    db.add(doc)
    await db.commit()

    # Dispatch background processing
    process_document_task.delay(
        doc_id    = doc_id,
        file_path = str(save_path),
        file_type = file_type,
        owner_id  = str(user.id),
    )

    logger.info(
        "Document uploaded",
        doc_id   = doc_id,
        filename = file.filename,
        size     = len(file_bytes),
    )

    return {
        "doc_id":   doc_id,
        "filename": file.filename,
        "type":     file_type,
        "status":   "pending",
        "message":  "Document queued for processing. Poll /status to track progress.",
    }


@router.get("")
async def list_documents(
    db:   AsyncSession = Depends(get_db),
    user               = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List all documents belonging to the current user."""
    query = (
        select(Document)
        .where(Document.owner_id == user.id)
        .order_by(desc(Document.uploaded_at))
    )

    if status:
        query = query.where(Document.status == status)

    result = await db.execute(query)
    docs   = result.scalars().all()

    return [_doc_to_dict(d) for d in docs]


@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    db:     AsyncSession = Depends(get_db),
    user                 = Depends(get_current_user),
):
    """Get full details of one document."""
    doc = await _get_doc_or_404(doc_id, user.id, db)
    return _doc_to_dict(doc, detailed=True)


@router.get("/{doc_id}/status")
async def get_document_status(
    doc_id: str,
    db:     AsyncSession = Depends(get_db),
    user                 = Depends(get_current_user),
):
    """
    Poll this endpoint after upload to track processing.
    Returns status: pending | processing | ready | failed
    """
    doc = await _get_doc_or_404(doc_id, user.id, db)

    return {
        "doc_id":        doc_id,
        "status":        doc.status,
        "page_count":    doc.page_count,
        "chunk_count":   doc.chunk_count,
        "error_message": doc.error_message,
        "processed_at":  doc.processed_at.isoformat() if doc.processed_at else None,
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db:     AsyncSession = Depends(get_db),
    user                 = Depends(get_current_user),
):
    """
    Delete a document.
    Removes: DB record, file from disk, vectors from Qdrant.
    """
    doc = await _get_doc_or_404(doc_id, user.id, db)

    # Delete vectors from Qdrant
    from services.retrieval.vector_store import VectorStore
    vs = VectorStore()
    await vs.delete_by_doc(doc_id)

    # Delete file from disk
    file_path = Path("uploads") / doc.filename
    delete_file(file_path)

    # Delete from DB (cascades to chunks)
    await db.delete(doc)
    await db.commit()

    logger.info("Document deleted", doc_id=doc_id)
    return {"message": "Document deleted successfully"}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

async def _get_doc_or_404(
    doc_id:  str,
    user_id,
    db:      AsyncSession,
) -> Document:
    """Fetch document by ID, verify ownership, raise 404 if missing."""
    result = await db.execute(
        select(Document).where(
            Document.id       == uuid.UUID(doc_id),
            Document.owner_id == user_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise DocumentNotFound(doc_id)
    return doc


def _doc_to_dict(doc: Document, detailed: bool = False) -> dict:
    """Convert Document model to response dict."""
    data = {
        "id":           str(doc.id),
        "filename":     doc.original_name,
        "type":         doc.file_type,
        "size_bytes":   doc.file_size,
        "size_mb":      round(doc.file_size / 1024 / 1024, 2),
        "status":       doc.status,
        "page_count":   doc.page_count,
        "chunk_count":  doc.chunk_count,
        "tags":         doc.tags,
        "uploaded_at":  doc.uploaded_at.isoformat(),
        "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
    }

    if detailed:
        data["doc_metadata"]  = doc.doc_metadata
        data["error_message"] = doc.error_message

    return data