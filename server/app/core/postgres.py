# app/core/postgres.py
from contextlib import asynccontextmanager
from app.database import AsyncSessionLocal # Import the async session factory

@asynccontextmanager
async def get_db_session():
    """
    Provides an async database session.
    The session is automatically closed after the 'with' block.
    """
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()