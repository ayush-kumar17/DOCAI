"""
Chat routes with SSE streaming.

POST /api/chat/sessions                      — create session
POST /api/chat/sessions/{id}/message         — send message (SSE stream)
GET  /api/chat/sessions                      — list sessions
GET  /api/chat/sessions/{id}/history         — get all messages
DELETE /api/chat/sessions/{id}               — delete session
PATCH /api/chat/sessions/{id}                — rename session
"""

import json
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete

from database.connection import get_db
from database.models import ChatSession, Message, Document
from auth.dependencies import get_current_user
from services.agent.rag_agent import RAGAgent
from utils.logger import get_logger
from utils.exceptions import SessionNotFound

logger = get_logger(__name__)
router = APIRouter()

# Single shared agent instance (graph is compiled once)
_agent: Optional[RAGAgent] = None

def get_agent() -> RAGAgent:
    global _agent
    if _agent is None:
        _agent = RAGAgent()
    return _agent


# ──────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    title:   str = "New Chat"
    doc_ids: List[str] = []


class SendMessageRequest(BaseModel):
    content: str
    doc_ids: Optional[List[str]] = None


class RenameSessionRequest(BaseModel):
    title: str


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@router.post("/sessions", status_code=201)
async def create_session(
    body: CreateSessionRequest,
    db:   AsyncSession = Depends(get_db),
    user               = Depends(get_current_user),
):
    """Create a new chat session."""
    session = ChatSession(
        user_id = user.id,
        title   = body.title,
        doc_ids = body.doc_ids,
    )
    db.add(session)
    await db.commit()

    return {
        "session_id": str(session.id),
        "title":      session.title,
        "doc_ids":    session.doc_ids,
        "created_at": session.created_at.isoformat(),
    }


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    body:       SendMessageRequest,
    db:         AsyncSession = Depends(get_db),
    user                    = Depends(get_current_user),
):
    """
    Send a message and stream the response as Server-Sent Events.

    Each SSE event is a JSON string with structure:
        data: {"type": "intent",    "data": "qa"}
        data: {"type": "chunks",    "data": 5}
        data: {"type": "token",     "data": "The "}
        data: {"type": "token",     "data": "answer "}
        data: {"type": "citations", "data": [...]}
        data: {"type": "done",      "data": {"confidence": 0.87, "latency_ms": 1234}}
        data: {"type": "error",     "data": "error message"}

    The frontend reads these events and updates the UI progressively.
    """
    # Verify session exists and belongs to user
    session = await _get_session_or_404(session_id, user.id, db)

    # Determine which docs to search
    doc_ids = body.doc_ids or session.doc_ids or []

    # If no docs specified, search all user's ready documents
    if not doc_ids:
        result  = await db.execute(
            select(Document.id)
            .where(Document.owner_id == user.id, Document.status == "ready")
        )
        doc_ids = [str(row[0]) for row in result.all()]

    # Load conversation history
    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in history_result.scalars().all()
    ]

    # Save user message immediately
    user_msg = Message(
        session_id = session.id,
        role       = "user",
        content    = body.content,
    )
    db.add(user_msg)
    await db.commit()

    async def event_stream():
        """Generator that yields SSE events."""
        start_ms   = time.time()
        agent      = get_agent()
        full_answer = []
        citations   = []
        confidence  = 0.0

        try:
            # Stream events from the agent
            async for event in agent.stream(
                query    = body.content,
                doc_ids  = doc_ids,
                owner_id = str(user.id),
                history  = history,
            ):
                event_type = event.get("type")

                if event_type == "token":
                    full_answer.append(event["data"])

                elif event_type == "citations":
                    citations = event["data"]

                elif event_type == "done":
                    confidence = event["data"].get("confidence", 0.0)

                # Send every event to the client
                yield f"data: {json.dumps(event)}\n\n"

            # Calculate total latency
            latency_ms = int((time.time() - start_ms) * 1000)

            # Send final done event with latency
            yield f"data: {json.dumps({'type': 'done', 'data': {'confidence': confidence, 'latency_ms': latency_ms}})}\n\n"

            # Save assistant message to DB
            answer_text = "".join(full_answer)

            if answer_text:
                assistant_msg = Message(
                    session_id = session.id,
                    role       = "assistant",
                    content    = answer_text,
                    citations  = citations,
                    latency_ms = float(latency_ms),
                )
                db.add(assistant_msg)

                # Auto-update session title from first message
                if len(history) == 0:
                    title = body.content[:60] + ("..." if len(body.content) > 60 else "")
                    session.title = title

                await db.commit()

        except Exception as e:
            logger.error(f"Agent error in stream: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type = "text/event-stream",
        headers    = {
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering":"no",       # Disable NGINX buffering for SSE
            "Connection":       "keep-alive",
        },
    )


@router.get("/sessions")
async def list_sessions(
    db:   AsyncSession = Depends(get_db),
    user               = Depends(get_current_user),
):
    """List all chat sessions for the current user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(desc(ChatSession.created_at))
    )
    sessions = result.scalars().all()

    return [
        {
            "id":         str(s.id),
            "title":      s.title,
            "doc_ids":    s.doc_ids,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}/history")
async def get_history(
    session_id: str,
    db:         AsyncSession = Depends(get_db),
    user                    = Depends(get_current_user),
):
    """Get all messages in a session."""
    session = await _get_session_or_404(session_id, user.id, db)

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return [
        {
            "id":         str(m.id),
            "role":       m.role,
            "content":    m.content,
            "citations":  m.citations,
            "latency_ms": m.latency_ms,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.patch("/sessions/{session_id}")
async def rename_session(
    session_id: str,
    body:       RenameSessionRequest,
    db:         AsyncSession = Depends(get_db),
    user                    = Depends(get_current_user),
):
    """Rename a chat session."""
    session       = await _get_session_or_404(session_id, user.id, db)
    session.title = body.title
    await db.commit()
    return {"message": "Session renamed", "title": body.title}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db:         AsyncSession = Depends(get_db),
    user                    = Depends(get_current_user),
):
    """Delete a session and all its messages."""
    session = await _get_session_or_404(session_id, user.id, db)
    await db.delete(session)
    await db.commit()
    return {"message": "Session deleted"}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

async def _get_session_or_404(
    session_id: str,
    user_id,
    db: AsyncSession,
) -> ChatSession:
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id      == uuid.UUID(session_id),
            ChatSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise SessionNotFound(session_id)
    return session