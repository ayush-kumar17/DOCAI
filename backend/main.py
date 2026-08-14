"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from config import settings
from database.connection import init_db
from utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    logger.info("Starting up", app=settings.APP_NAME, env=settings.APP_ENV)
    await init_db()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title       = settings.APP_NAME,
    description = "Enterprise AI-powered document search and Q&A",
    version     = "1.0.0",
    lifespan    = lifespan,
    docs_url    = "/api/docs",
    redoc_url   = "/api/redoc",
)

# ── Middleware ────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.cors_origins,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ───────────────────────────────────
from auth.routes import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

# Phase 3+ routers added here as we build them:
# from api.routes.documents import router as doc_router
# app.include_router(doc_router, prefix="/api/documents", tags=["Documents"])


@app.get("/health", tags=["Health"])
async def health():
    """Quick health check — used by Docker and load balancers."""
    return {"status": "ok", "version": "1.0.0"}


from api.routes.documents import router as doc_router
app.include_router(doc_router, prefix="/api/documents", tags=["Documents"])


from api.routes.chat import router as chat_router
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])