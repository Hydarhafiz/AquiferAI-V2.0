# app/services/chat_service.py

import uuid
from datetime import datetime, timezone # <--- THIS LINE MUST BE CHANGED
from typing import List, Dict, Any, Optional
from uuid import UUID
import json

from app.core.postgres import get_db_session
from sqlalchemy import text
from app.services.aquifer_service import generate_aquifer_summary
from app.config import SLIDING_WINDOW_K, SUMMARY_TRIGGER_THRESHOLD



# --- Database Functions (all updated to use async with get_db_session) ---

async def get_chat_history(session_id: UUID, limit: int = None) -> List[Dict[str, Any]]:
    """Retrieves chat history for a given session, optionally limited."""
    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT history FROM chat_sessions WHERE session_id = :session_id"),
            {"session_id": session_id}
        )
        row = result.fetchone()
        if row and row[0]:
            try:
                history = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            except json.JSONDecodeError:
                history = []
                print(f"Warning: Failed to decode history for session {session_id}. History might be malformed JSON.")
            return history[-limit:] if limit else history
        return []

async def get_chat_summary(session_id: UUID) -> Optional[str]:
    """Retrieves the summary for a given chat session."""
    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT summary FROM chat_sessions WHERE session_id = :session_id"),
            {"session_id": session_id}
        )
        row = result.fetchone()
        return row[0] if row else None


async def add_message_to_session(session_id: UUID, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
    """Adds a new message to the history of a chat session."""
    async with get_db_session() as session:
        # Get current history (fetch fresh to avoid stale data if multiple updates are rapid)
        current_history_result = await session.execute(
            text("SELECT history FROM chat_sessions WHERE session_id = :session_id"),
            {"session_id": session_id}
        )
        current_history_row = current_history_result.fetchone()

        current_history = []
        if current_history_row and current_history_row[0]:
            try:
                current_history = json.loads(current_history_row[0]) if isinstance(current_history_row[0], str) else current_history_row[0]
            except json.JSONDecodeError:
                print(f"Warning: Failed to decode existing history for session {session_id} during add_message. Starting with empty history.")
                current_history = []

        # Add new message
        new_message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat() # <--- THIS LINE MUST BE CHANGED
        }
        if metadata:
            new_message["metadata"] = metadata
        current_history.append(new_message)

        # Update the session with the new history
        await session.execute(
            text("""
                UPDATE chat_sessions
                SET history = :history, last_updated = NOW()
                WHERE session_id = :session_id
            """),
            {"history": json.dumps(current_history), "session_id": session_id}
        )
        await session.commit()
    print(f"Message added to session {session_id}: {role} - {content[:50]}...")


async def update_chat_session_summary(session_id: UUID, new_summary: str):
    """Updates the summary of a chat session."""
    async with get_db_session() as session:
        await session.execute(
            text("""
                UPDATE chat_sessions
                SET summary = :summary, last_updated = NOW()
                WHERE session_id = :session_id
            """),
            {"summary": new_summary, "session_id": session_id}
        )
        await session.commit()
    print(f"Updated summary for session {session_id}.")


async def create_chat_session(title: str = "New Chat") -> UUID:
    """Creates a new chat session in the database."""
    session_id = uuid.uuid4()
    async with get_db_session() as session:
        await session.execute(
            text("""
                INSERT INTO chat_sessions (session_id, title, history, summary, created_at, last_updated)
                VALUES (:session_id, :title, :history, :summary, :created_at, :last_updated)
            """),
            {
                "session_id": session_id,
                "title": title,
                "history": json.dumps([]),
                "summary": "",
                "created_at": datetime.now(timezone.utc), # <--- THIS LINE MUST BE CHANGED
                "last_updated": datetime.now(timezone.utc) # <--- THIS LINE MUST BE CHANGED
            }
        )
        await session.commit()
    print(f"Created new chat session: {session_id}")
    return session_id

async def delete_chat_session(session_id: UUID):
    """Deletes a chat session from the database."""
    async with get_db_session() as session:
        result = await session.execute(
            text("DELETE FROM chat_sessions WHERE session_id = :session_id RETURNING session_id"),
            {"session_id": session_id}
        )
        if result.fetchone() is None:
            raise ValueError(f"Session with ID {session_id} not found.")
        await session.commit()
    print(f"Deleted chat session: {session_id}")

async def update_session_title(session_id: UUID, new_title: str):
    """Updates the title of a chat session."""
    async with get_db_session() as session:
        result = await session.execute(
            text("UPDATE chat_sessions SET title = :new_title, last_updated = NOW() WHERE session_id = :session_id RETURNING session_id"),
            {"new_title": new_title, "session_id": session_id}
        )
        if result.fetchone() is None:
            raise ValueError(f"Session with ID {session_id} not found.")
        await session.commit()
    print(f"Updated session {session_id} title to: {new_title}")

async def get_all_chat_sessions() -> List[Dict[str, Any]]:
    """Retrieves metadata for all chat sessions."""
    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT session_id, title, created_at, last_updated FROM chat_sessions ORDER BY last_updated DESC")
        )
        sessions_data = []
        for row in result.fetchall():
            sessions_data.append({
                "session_id": str(row[0]), # Convert the asyncpg UUID object to its string representation
                "title": row[1],
                "created_at": row[2].isoformat(),
                "last_updated": row[3].isoformat()
            })
        return sessions_data

# Utility to convert DB JSONB format to Ollama's message format
def _convert_db_history_to_ollama_messages(db_history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Converts the history stored in DB (JSONB) to Ollama's expected message format."""
    ollama_messages = []
    for msg_data in db_history:
        if msg_data["role"] in ["user", "assistant", "tool", "system"]:
            ollama_messages.append({"role": msg_data["role"], "content": msg_data["content"]})
        else:
            print(f"Warning: Unexpected role '{msg_data['role']}' in history. Skipping for Ollama.")
    return ollama_messages


# --- Main Chat Processing Function ---

async def process_chat_message(session_id: Optional[UUID], user_message: str) -> tuple[UUID, str, List[Dict[str, Any]]]:
    """
    Processes a user's chat message, retrieves history, calls aquifer service,
    stores messages, and potentially summarizes history.
    """
    current_summary = None

    if session_id is None:
        session_id = await create_chat_session()
        current_history_from_db: List[Dict[str, Any]] = []
    else:
        current_history_from_db = await get_chat_history(session_id)
        current_summary = await get_chat_summary(session_id)

    # 1. Prepare messages for the LLM
    messages_for_ollama: List[Dict[str, str]] = [] # Ollama expects 'role' and 'content' only

    if current_summary:
        messages_for_ollama.append({"role": "system", "content": f"Previous conversation summary: {current_summary}"})

    # Get recent messages from DB for LLM context
    recent_messages_for_llm = current_history_from_db[-SLIDING_WINDOW_K:]
    messages_for_ollama.extend(_convert_db_history_to_ollama_messages(recent_messages_for_llm))

    print(f"Messages sent to Aquifer Service for LLM (including summary if present, total {len(messages_for_ollama)}):")
    for msg in messages_for_ollama:
        print(f"   {msg['role']}: {msg['content'][:70]}...")

    # 2. Add the user's message to the history first (without metadata)
    await add_message_to_session(session_id=session_id, role="user", content=user_message)

    # 3. Call generate_aquifer_summary to get AI response AND metadata
    aquifer_analysis_result = await generate_aquifer_summary(
        user_prompt=user_message,
        chat_history=messages_for_ollama, # Pass the LLM-formatted history
    )
    ai_response_content = aquifer_analysis_result.get("ai_response", "I could not process that request.")

    # --- START CHANGE: Extract and pass metadata ---
    response_statistics = aquifer_analysis_result.get("statistics")
    response_objectids = aquifer_analysis_result.get("objectids")
    response_cypher_queries = aquifer_analysis_result.get("cypher_queries") # Assuming it's already a list or single item to be wrapped

    # Build the metadata dictionary
    assistant_message_metadata: Dict[str, Any] = {}
    if response_statistics:
        assistant_message_metadata["statistics"] = response_statistics
    if response_objectids:
        # Ensure objectids are strings for frontend consistency (e.g., "43445")
        assistant_message_metadata["objectids"] = [str(oid) for oid in response_objectids]
    if response_cypher_queries:
        # Ensure cypher_queries is a list for consistency
        assistant_message_metadata["cypher_queries"] = response_cypher_queries

    # Add the assistant's message with metadata to the history
    await add_message_to_session(
        session_id=session_id,
        role="assistant",
        content=ai_response_content,
        metadata=assistant_message_metadata if assistant_message_metadata else None # Pass None if empty
    )
    # --- END CHANGE ---

    # 4. Re-fetch the full history to include the newly added messages (user and assistant)
    # This is crucial because add_message_to_session updates the DB, not the in-memory list
    full_history_after_additions = await get_chat_history(session_id)

    # 5. Summarization logic (remains mostly the same)
    if len(full_history_after_additions) > SUMMARY_TRIGGER_THRESHOLD:
        print(f"History length ({len(full_history_after_additions)} messages) exceeds threshold ({SUMMARY_TRIGGER_THRESHOLD}). Initiating summarization...")

        # Get messages to summarize (all but the sliding window)
        messages_to_summarize_data = full_history_after_additions[:-SLIDING_WINDOW_K]

        conversation_text_to_summarize = ""
        if current_summary:
            conversation_text_to_summarize += f"Previous Summary: {current_summary}\n\n"

        conversation_text_to_summarize += "\n".join([
            f"{msg['role'].capitalize()}: {msg['content']}"
            for msg in messages_to_summarize_data
        ])

        try:
            # Dynamically import to avoid circular dependency if ollama_service depends on chat_service
            from app.services.ollama_service import get_ollama_summary
            new_segment_summary = await get_ollama_summary(conversation_text_to_summarize)
            print(f"Generated new summary segment: {new_segment_summary[:100]}...")

            await update_chat_session_summary(session_id, new_segment_summary)

            # Trim the history in the DB (keep only the sliding window)
            async with get_db_session() as session:
                trimmed_history = full_history_after_additions[-SLIDING_WINDOW_K:]
                await session.execute(
                    text("""
                        UPDATE chat_sessions
                        SET history = :history, last_updated = NOW()
                        WHERE session_id = :session_id
                    """),
                    {"history": json.dumps(trimmed_history), "session_id": session_id}
                )
                await session.commit()
            print(f"History trimmed in DB to {len(trimmed_history)} messages.")
            # Update the in-memory full_history_after_additions to reflect the trimmed history
            full_history_after_additions = trimmed_history

        except ImportError:
            print("Warning: app.services.ollama_service.get_ollama_summary not found. Skipping summarization.")
        except Exception as e:
            print(f"Error during summarization: {e}")

    return session_id, ai_response_content, full_history_after_additions