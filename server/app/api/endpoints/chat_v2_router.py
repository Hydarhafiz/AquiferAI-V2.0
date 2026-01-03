"""
FastAPI router for V2 chat endpoints with LangGraph workflow integration.

This router replaces the legacy Ollama-based chat with the new multi-agent workflow.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import logging

from app.graph.workflow import execute_workflow
from app.graph.state import ExecutionTraceStep
from app.services.chat_service import (
    create_chat_session,
    get_all_chat_sessions,
    get_chat_history,
    update_session_title,
    delete_chat_session,
    save_chat_message  # We'll need to create this function
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["chat-v2"])


# Request/Response Models
class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""
    message: str = Field(..., description="The user's message", min_length=1)
    session_id: Optional[str] = Field(None, description="Session ID (creates new if not provided)")
    expert_mode: bool = Field(False, description="Enable expert mode to see query details")


class ExecutionTraceResponse(BaseModel):
    """Response model for execution trace in expert mode."""
    agent: str
    duration_ms: float
    status: str
    retry_count: int = 0
    details: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    """Response model for chat message."""
    session_id: str
    ai_response: str
    execution_trace: Optional[List[ExecutionTraceResponse]] = None
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata (query stats, performance, etc.)"
    )


class CreateSessionRequest(BaseModel):
    """Request model for creating a new session."""
    title: Optional[str] = Field("New Chat", description="Session title")


class UpdateTitleRequest(BaseModel):
    """Request model for updating session title."""
    new_title: str = Field(..., description="New title for the session")


# Endpoints

@router.post("/chat/message", response_model=ChatMessageResponse)
async def send_chat_message(request: ChatMessageRequest):
    """
    Send a message and get AI response using LangGraph workflow.

    This endpoint:
    1. Creates a new session if needed
    2. Executes the multi-agent workflow
    3. Returns the formatted response
    4. Optionally includes execution trace in expert mode
    """
    try:
        # Create or validate session
        if request.session_id:
            try:
                session_id = UUID(request.session_id)
                # Verify session exists
                all_sessions = await get_all_chat_sessions()
                if not any(s['session_id'] == str(session_id) for s in all_sessions):
                    raise HTTPException(status_code=404, detail="Session not found")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid session_id format")
        else:
            # Create new session
            session_id = await create_chat_session(title="New Chat")

        logger.info(f"Processing message for session {session_id} (expert_mode={request.expert_mode})")

        # Execute LangGraph workflow
        final_state = await execute_workflow(
            user_query=request.message,
            session_id=str(session_id),
            expert_mode=request.expert_mode
        )

        # Extract response
        ai_response = final_state.get("final_response", "I apologize, but I couldn't generate a response.")

        # Build execution trace for expert mode
        execution_trace = None
        if request.expert_mode:
            trace_steps = final_state.get("execution_trace", [])
            if trace_steps:
                execution_trace = [
                    ExecutionTraceResponse(
                        agent=step.agent,
                        duration_ms=step.duration_ms,
                        # ExecutionTraceStep uses 'error' field, derive status from it
                        status="error" if step.error else "success",
                        # retry_count is in output dict for validator, default to 0
                        retry_count=step.output.get("total_retries", 0) if step.output else 0,
                        details=step.output if step.output else None
                    )
                    for step in trace_steps
                ]

        # Build metadata
        metadata = {
            "complexity": final_state.get("query_plan").complexity if final_state.get("query_plan") else None,
            "queries_executed": len(final_state.get("validation_results", [])),
            "total_retries": final_state.get("total_retries", 0),
            "all_queries_valid": final_state.get("all_queries_valid", False)
        }

        # Save to chat history (async operation, don't block response)
        try:
            await save_chat_message(
                session_id=session_id,
                user_message=request.message,
                ai_response=ai_response
            )
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")
            # Don't fail the request if history save fails

        return ChatMessageResponse(
            session_id=str(session_id),
            ai_response=ai_response,
            execution_trace=execution_trace,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )


@router.post("/chat/sessions", response_model=Dict[str, str])
async def create_new_session(request: CreateSessionRequest = CreateSessionRequest()):
    """Create a new chat session."""
    try:
        session_id = await create_chat_session(title=request.title)
        return {
            "session_id": str(session_id),
            "title": request.title
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/chat/sessions")
async def list_sessions():
    """List all chat sessions."""
    try:
        sessions = await get_all_chat_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/chat/sessions/{session_id}/history")
async def get_session_history_endpoint(session_id: UUID):
    """Get chat history for a specific session."""
    try:
        history = await get_chat_history(session_id)
        if history is None:
            # Check if session exists
            all_sessions = await get_all_chat_sessions()
            if not any(s['session_id'] == str(session_id) for s in all_sessions):
                raise HTTPException(status_code=404, detail="Session not found")

        return {
            "session_id": str(session_id),
            "history": history or []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.put("/chat/sessions/{session_id}/title")
async def update_title_endpoint(session_id: UUID, request: UpdateTitleRequest):
    """Update the title of a chat session."""
    try:
        await update_session_title(session_id, request.new_title)
        return {"message": "Title updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating title: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update title: {str(e)}")


@router.delete("/chat/sessions/{session_id}")
async def delete_session_endpoint(session_id: UUID):
    """Delete a chat session."""
    try:
        await delete_chat_session(session_id)
        return {"message": "Session deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/chat/health")
async def health_check():
    """Health check endpoint for V2 chat service."""
    return {
        "status": "healthy",
        "version": "2.0",
        "workflow": "langgraph",
        "agents": ["planner", "cypher-specialist", "validator", "analyst"]
    }
