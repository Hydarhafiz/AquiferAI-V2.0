# app/database.py (Revised for Async Support)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# Get database URL from environment variables
# Ensure your DATABASE_URL starts with 'postgresql+asyncpg://' for async
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/co2_chat_db")

# Create SQLAlchemy AsyncEngine
# pool_pre_ping is for synchronous engines; for async, connection testing is usually different
engine = create_async_engine(DATABASE_URL, echo=False) # Set echo=True for SQL logging

# Async Session factory
AsyncSessionLocal = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# Base class for models
Base = declarative_base()