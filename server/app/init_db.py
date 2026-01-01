# app/init_db.py (Revised)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.database import Base # Assuming Base is defined here
from app.models import chat_models
import os
import asyncio

# Use the same DATABASE_URL logic as app/database.py for consistency
# Ensure your DATABASE_URL environment variable is set to postgresql+asyncpg://
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/co2_chat_db")

async def init_db_async(): # Changed to an async function
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set.")

    
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn: # Use async connection for DDL operations
        print("Dropping all existing database tables (if any)...")
        await conn.run_sync(Base.metadata.drop_all) # run_sync for sync DDL operations
        print("Creating new database tables...")
        await conn.run_sync(Base.metadata.create_all) # run_sync for sync DDL operations
    print("Database tables created.")

    await engine.dispose() # Properly close the engine after use

if __name__ == '__main__':
    # This part is for running init_db.py directly
    asyncio.run(init_db_async()) # Run the async function