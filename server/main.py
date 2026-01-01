# main.py
import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# --- MODIFICATION HERE ---
from app.init_db import init_db_async # Import the async init function
# --- END MODIFICATION ---
from app.api.endpoints import aquifer_router, chat_router

app = FastAPI(
    title="CO2 Aquifer Suitability API",
    description="API for analyzing CO2 storage suitability in saline aquifers.",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    # Wait for dependencies to be ready
    print("Waiting for dependencies to be ready...")
    time.sleep(10)  # Initial buffer

    # Initialize database if needed
    if os.getenv("INIT_DB", "false").lower() == "true":
        print("Initializing database...")
        try:
            # --- MODIFICATION HERE ---
            await init_db_async() # Await the async init function
            # --- END MODIFICATION ---
            print("Database initialized.")
        except Exception as e:
            print(f"Database initialization failed: {e}")
            # Consider re-raising the exception or exiting if DB is critical for startup
            # raise # Uncomment to prevent app from starting if DB init fails

# Add CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(aquifer_router.router, prefix="/api")
app.include_router(chat_router.router, prefix="/chat")