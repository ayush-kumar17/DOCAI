"""
Database connection — async SQLAlchemy engine.

get_db() is a FastAPI dependency injected into every route
that needs database access.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Create async engine
# pool_size: number of persistent connections
# max_overflow: extra connections allowed above pool_size
# echo: log all SQL (only in debug mode)
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
    pool_pre_ping=True,   # verify connections are alive before using
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep objects usable after commit
    autoflush=False,
    autocommit=False,
)


async def get_db():
    """
    FastAPI dependency — provides a DB session per request.

    Usage in a route:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Create all tables on startup.
    In production use Alembic migrations instead.
    """
    from database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created/verified")