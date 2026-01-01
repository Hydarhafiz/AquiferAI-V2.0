# app/services/ollama_service.py
import logging
import os
import re
from typing import Dict, List, Any, Optional
# import requests # Removed, replaced by httpx
import httpx # New import for async HTTP requests
import json
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_CHAT_ENDPOINT = f"{OLLAMA_BASE_URL}/api/chat"
GENERATE_CYPHER_MODEL = os.getenv("GENERATE_CYPHER_MODEL", "qwen2.5-coder:7b") # This model will still be used but via query_ollama_with_history
AI_CHATBOT_MODEL = os.getenv("AI_CHATBOT_MODEL", "llama3:8b")
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "llama3:8b") # Ensure this is read correctly

# System prompts (assuming these are defined in app.utils.setup_prompt)
from app.utils.setup_prompt import SUMMARY_SYSTEM_PROMPT # Updated import for CYPHER_SYSTEM

# Define a custom exception for retries specifically for network errors
class OllamaNetworkError(httpx.RequestError):
    """Custom exception for Ollama network errors that should trigger a retry."""
    pass

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5), retry=retry_if_exception_type(OllamaNetworkError))
async def _call_ollama_chat_api(messages: List[Dict[str, str]], model: str, stream: bool = False, options: Dict = None) -> Dict:
    """Helper to call the Ollama chat API with retry logic using httpx."""
    headers = {"Content-Type": "application/json"}

    # The `messages` list is assumed to be fully prepared by the caller,
    # including any system prompts at the beginning.
    payload = {
        "model": model,
        "messages": messages, # Use messages directly
        "stream": stream,
        "options": options if options is not None else {}
    }
    logger.info(f"Calling Ollama chat API with model: {model}, messages count: {len(messages)}...")
    
    async with httpx.AsyncClient(timeout=300) as client: # Use httpx.AsyncClient
        try:
            response = await client.post(OLLAMA_CHAT_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses
            return response.json()
        except httpx.TimeoutException:
            logger.error(f"Ollama API call timed out after {client.timeout} seconds for model {model}.")
            raise HTTPException(status_code=504, detail=f"Ollama service timed out: {model}")
        except httpx.RequestError as e: # Catch all httpx request errors
            logger.error(f"Error calling Ollama chat API for model {model}: {e}")
            response_text = response.text if 'response' in locals() and response else 'N/A'
            logger.error(f"Ollama response content: {response_text}")
            raise OllamaNetworkError(f"Network error with Ollama service: {e}") from e # Raise custom error for retry
        except httpx.HTTPStatusError as e: # Catch specific HTTP status errors
            logger.error(f"Ollama API returned non-2xx status for model {model}: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Ollama service error: {e.response.text}")


async def query_ollama_with_history(messages: List[Dict[str, str]], model: str = AI_CHATBOT_MODEL, system_prompt: Optional[str] = None) -> str:
    """
    Queries Ollama for a general AI response given a list of messages (including history).
    The messages list should already include any necessary system prompts as its first element.
    """
    
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages) # Add the rest of the conversation history
    
    options = {
        "temperature": 0.3,
        "num_ctx": 8192,
        "top_k": 30,
        "top_p": 0.9,
        "repeat_penalty": 1.1
    }

    try:
        # Pass the messages list directly, assuming it's already correctly structured
        # (e.g., system prompt, then user/assistant history)
        response_data = await _call_ollama_chat_api(
            messages=full_messages,
            model=model, # Use the model passed or default to AI_CHATBOT_MODEL
            options=options
        )
        return response_data.get("message", {}).get("content", "").strip()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during AI response generation: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error during AI response generation: {e}")

async def get_ollama_summary(conversation_text: str) -> str:
    """Generates a concise summary of the given conversation text using a dedicated summary model."""
    # Ensure SUMMARY_SYSTEM_PROMPT is the first message for the LLM
    messages = [{"role": "system", "content": SUMMARY_SYSTEM_PROMPT}, 
                {"role": "user", "content": conversation_text}]

    options = {
        "temperature": 0.5,
        "num_ctx": 4096, # Adjust context window for summary model if it's smaller
        "top_k": 20,
        "top_p": 0.8,
    }

    try:
        response_data = await _call_ollama_chat_api(
            messages=messages, # Pass the prepared messages list
            model=SUMMARY_MODEL,
            options=options
        )
        return response_data.get("message", {}).get("content", "").strip()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {e}")


def sanitize_cypher(cypher: str) -> str:
    """
    Sanitizes a Cypher query to prevent injection attacks or unintended operations.
    This function remains the same.
    """
    if re.search(r"(CREATE|SET|DELETE|REMOVE|DETACH|MERGE|ON CREATE|ON MATCH)\b", cypher, re.IGNORECASE):
        raise ValueError("Cypher query contains disallowed write operations.")
    if re.search(r"(LOAD CSV|CALL dbms\.security|apoc\.)\b", cypher, re.IGNORECASE):
        raise ValueError("Cypher query contains disallowed procedures or functions.")
    return cypher