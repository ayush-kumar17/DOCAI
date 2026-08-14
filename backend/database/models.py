"""
All database models in one file.
Tables:
  - users
  - documents
  - chunks
  - chat_sessions
  - messages

Relationships:
  User → Documents (one to many)
  Document → Chunks (one to many)
  User → ChatSessions (one to many)
  ChatSession → Messages (one to many)
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, DateTime,
    Text, ForeignKey, JSON, Boolean, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
# User
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    username   = Column(String(100), unique=True, nullable=False)
    hashed_pw  = Column(String(255), nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents     = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"


# ──────────────────────────────────────────────
# Document
# ──────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # File info
    filename      = Column(String(500), nullable=False)       # saved name on disk: {uuid}.pdf
    original_name = Column(String(500), nullable=False)       # what the user uploaded
    file_type     = Column(String(50),  nullable=False)       # pdf, docx, pptx, xlsx, csv, txt, md, png, jpg
    file_size     = Column(BigInteger,  nullable=False)       # bytes

    # Processing status
    # pending → processing → ready
    #                      → failed
    status        = Column(String(50), default="pending", nullable=False, index=True)
    error_message = Column(Text, nullable=True)               # set if status = failed

    # Post-processing stats
    page_count    = Column(Integer, default=0)
    chunk_count   = Column(Integer, default=0)

    # Extra metadata extracted from the document
    # e.g. {"title": "...", "author": "...", "subject": "..."}
    doc_metadata  = Column(JSON, default=dict)

    # User-defined tags
    tags          = Column(JSON, default=list)

    # Timestamps
    uploaded_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at  = Column(DateTime, nullable=True)

    # Relationships
    owner  = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document id={self.id} name={self.original_name} status={self.status}>"


# ──────────────────────────────────────────────
# Chunk
# ──────────────────────────────────────────────

class Chunk(Base):
    __tablename__ = "chunks"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Position in document
    chunk_index = Column(Integer, nullable=False)   # 0-based index within document
    page_number = Column(Integer, nullable=True)    # which page this came from
    section     = Column(String(500), nullable=True) # heading/section name if detected

    # Content
    text        = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)

    # Content type flags
    has_table   = Column(Boolean, default=False)
    has_image   = Column(Boolean, default=False)

    # Link back to Qdrant vector
    # Stored so we can delete vectors when document is deleted
    vector_id   = Column(String(100), nullable=True)

    # Extra metadata
    chunk_metadata = Column(JSON, default=dict)

    # Relationship
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<Chunk id={self.id} doc={self.document_id} index={self.chunk_index}>"


# ──────────────────────────────────────────────
# ChatSession
# ──────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title      = Column(String(500), default="New Chat", nullable=False)

    # Which documents are in scope for this session
    # Stored as list of doc_id strings
    doc_ids    = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user     = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession id={self.id} title={self.title}>"


# ──────────────────────────────────────────────
# Message
# ──────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    role       = Column(String(20), nullable=False)   # "user" or "assistant"
    content    = Column(Text, nullable=False)

    # Citations attached to assistant messages
    # Format: [{"doc_id": "...", "page": 5, "section": "...", "confidence": 0.92, "text_snippet": "..."}]
    citations  = Column(JSON, default=list)

    # Performance tracking
    latency_ms = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<Message id={self.id} role={self.role}>"