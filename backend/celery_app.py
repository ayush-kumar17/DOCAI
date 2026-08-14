"""
Celery Application

Handles background document processing so that:
  1. Upload returns immediately (fast response to user)
  2. Heavy processing (OCR, embedding) runs in background
  3. User sees status: pending → processing → ready

Run the worker with:
    PYTHONPATH=$(pwd) celery -A celery_app worker --loglevel=info --concurrency=2
"""

import asyncio
from celery import Celery
from config import settings


# ------------------------------------------------------------------
# Celery App
# ------------------------------------------------------------------

app = Celery(
    "docai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_soft_time_limit=600,
    task_time_limit=900,
    worker_prefetch_multiplier=1,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def run_async(coro):
    """Run async coroutine from synchronous Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def clean_text(text: str) -> str:
    """
    Remove characters PostgreSQL cannot store.
    """

    if text is None:
        return ""

    # PostgreSQL rejects NULL bytes
    text = text.replace("\x00", "")

    return text


# ------------------------------------------------------------------
# Celery Task
# ------------------------------------------------------------------

@app.task(
    bind=True,
    name="process_document",
    max_retries=3,
    default_retry_delay=60,
)
def process_document_task(
    self,
    doc_id: str,
    file_path: str,
    file_type: str,
    owner_id: str,
):
    return run_async(
        _process_document_async(
            self,
            doc_id,
            file_path,
            file_type,
            owner_id,
        )
    )


# ------------------------------------------------------------------
# Async Processing
# ------------------------------------------------------------------

async def _process_document_async(
    task,
    doc_id,
    file_path,
    file_type,
    owner_id,
):
    import uuid
    from datetime import datetime

    from sqlalchemy import update

    from database.connection import AsyncSessionLocal
    from database.models import Chunk, Document
    from services.document.processor import DocumentProcessor
    from utils.logger import get_logger

    logger = get_logger("celery.process_document")

    async with AsyncSessionLocal() as db:

        try:

            # ----------------------------------------------------------
            # Mark Processing
            # ----------------------------------------------------------

            await db.execute(
                update(Document)
                .where(Document.id == uuid.UUID(doc_id))
                .values(status="processing")
            )

            await db.commit()

            logger.info(
                "Document marked as processing",
                doc_id=doc_id,
            )

            # ----------------------------------------------------------
            # Run Processing Pipeline
            # ----------------------------------------------------------

            processor = DocumentProcessor()

            result = await processor.process(
                file_path=file_path,
                doc_id=doc_id,
                file_type=file_type,
                owner_id=owner_id,
            )

            logger.info(
                "Pipeline complete",
                chunks=result["chunk_count"],
                pages=result["page_count"],
            )

            # ----------------------------------------------------------
            # Build Chunk Objects
            # ----------------------------------------------------------

            chunk_objs = []

            for c in result["chunks"]:

                chunk_objs.append(

                    Chunk(
                        document_id=uuid.UUID(doc_id),

                        chunk_index=c["chunk_index"],

                        text=clean_text(
                            c.get("text", "")
                        ),

                        page_number=c.get("page_number"),

                        section=c.get("section", ""),

                        has_table=c.get(
                            "has_table",
                            False,
                        ),

                        has_image=c.get(
                            "has_image",
                            False,
                        ),

                        token_count=c.get(
                            "token_count",
                            0,
                        ),

                        vector_id=c.get("vector_id"),

                        chunk_metadata={},
                    )

                )

            db.add_all(chunk_objs)

            # Commit chunk insertion first
            await db.commit()

            logger.info(
                "Saved chunks",
                count=len(chunk_objs),
            )

            # ----------------------------------------------------------
            # Mark Ready
            # ----------------------------------------------------------

            await db.execute(
                update(Document)
                .where(Document.id == uuid.UUID(doc_id))
                .values(
                    status="ready",
                    page_count=result["page_count"],
                    chunk_count=result["chunk_count"],
                    processed_at=datetime.utcnow(),
                )
            )

            await db.commit()

            logger.info(
                "Document processing complete",
                doc_id=doc_id,
                page_count=result["page_count"],
                chunk_count=result["chunk_count"],
            )

            return {
                "doc_id": doc_id,
                "page_count": result["page_count"],
                "chunk_count": result["chunk_count"],
            }

        except Exception as exc:

            # IMPORTANT
            # Rollback failed transaction before doing anything else.
            await db.rollback()

            logger.exception(
                "Document processing failed",
                doc_id=doc_id,
            )

            try:

                await db.execute(
                    update(Document)
                    .where(Document.id == uuid.UUID(doc_id))
                    .values(
                        status="failed",
                        error_message=str(exc),
                    )
                )

                await db.commit()

            except Exception:

                await db.rollback()

            raise task.retry(
                exc=exc,
                countdown=60,
            )