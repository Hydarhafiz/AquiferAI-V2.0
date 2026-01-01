from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from uuid import UUID


from app.services.chat_service import (
    process_chat_message,
    create_chat_session,
    get_all_chat_sessions,
    get_chat_history,
    update_session_title,
    delete_chat_session
)

router = APIRouter()

@router.post("/message")
async def send_chat_message(
    user_input: Dict[str, str], # Expects {"session_id": "...", "message": "..."} or {"message": "..."}
):
    """
    Sends a user message to the chat and gets an AI response.
    If no session_id is provided, a new session is created.
    """
    session_id_str = user_input.get("session_id")
    user_message = user_input.get("message")

    if not user_message:
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")

    session_id: Optional[UUID] = None
    if session_id_str:
        try:
            session_id = UUID(session_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id format.")

    try:
        new_session_id, ai_response, history = await process_chat_message(
            session_id=session_id,
            user_message=user_message
        )
        return {
            "session_id": str(new_session_id),
            "ai_response": ai_response,
            "full_history": history # Return full history for client display
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.post("/sessions")
async def create_new_chat_session(
    # request_body: Optional[CreateChatSessionRequest] = None # If you have a Pydantic model for creation
):
    """Creates a new chat session."""
    # title = request_body.title if request_body and request_body.title else "New Chat"
    title = "New Chat" # For simplicity, if no schema is used yet
    new_id = await create_chat_session(title=title)
    return {"session_id": str(new_id), "title": title}

@router.get("/sessions")
async def get_all_sessions():
    """Retrieves a list of all chat sessions."""
    sessions = await get_all_chat_sessions()
    return {"sessions": sessions}

@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: UUID):
    """Retrieves the full chat history for a specific session."""
    history = await get_chat_history(session_id)
    if not history:
        # Check if the session actually exists, not just empty history
        all_sessions = await get_all_chat_sessions()
        if not any(s['session_id'] == str(session_id) for s in all_sessions): 
            raise HTTPException(status_code=404, detail=f"Session with ID {session_id} not found.")
        
    return {"session_id": str(session_id), "history": history}

@router.put("/sessions/{session_id}/title")
async def update_session_title_endpoint(session_id: UUID, new_title_data: Dict[str, str]):
    """Updates the title of a specific chat session."""
    new_title = new_title_data.get("new_title")
    if not new_title:
        raise HTTPException(status_code=400, detail="New title is required.")
    try:
        await update_session_title(session_id, new_title)
        return {"message": f"Session {session_id} title updated to '{new_title}'."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update title: {e}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: UUID):
    """Deletes a specific chat session."""
    try:
        await delete_chat_session(session_id)
        return {"message": f"Session {session_id} deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {e}")