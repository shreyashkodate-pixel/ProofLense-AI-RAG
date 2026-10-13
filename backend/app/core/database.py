"""ProofLens AI — Asynchronous Database Engine & Session Factory.

Manages PostgreSQL connection pooling, async session lifecycles, and health probe queries.
"""

from typing import AsyncGenerator, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.core.logging import logger

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def normalize_database_url(url: str) -> str:
    """Normalize database connection string to asyncpg dialect."""
    if not url:
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def get_engine() -> AsyncEngine:
    """Get or create singleton asynchronous engine."""
    global _engine, _sessionmaker
    if _engine is None:
        settings: Settings = get_settings()
        db_url = normalize_database_url(settings.DATABASE_URL)
        if not db_url:
            raise RuntimeError("Cannot initialize database engine: DATABASE_URL is not set.")

        _engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        _sessionmaker = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create singleton async sessionmaker."""
    global _sessionmaker
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def close_engine() -> None:
    """Dispose of the database engine on shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
        logger.info("Database engine connection pool closed.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connectivity(session: AsyncSession) -> bool:
    """Execute simple ping query to confirm database connectivity."""
    try:
        result = await session.execute(text("SELECT 1;"))
        return result.scalar() == 1
    except Exception as exc:
        logger.warning(f"Database connectivity check failed: {exc}")
        return False


async def check_pgvector_extension(session: AsyncSession) -> bool:
    """Verify that the pgvector extension is installed in the connected database."""
    try:
        result = await session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
        )
        return result.scalar() == 1
    except Exception as exc:
        logger.warning(f"pgvector extension check failed: {exc}")
        return False
