# app/config.py

# Memory Configuration for chat_service
# Adjust based on your chosen LLM's context window and desired short-term memory.
# Llama3 8B context window is typically 8192 tokens.
# A rough estimate: 1 message (user or AI) is ~50-100 tokens.
# So, 10-15 messages (5-7 pairs) might be a good starting point for the window.
SLIDING_WINDOW_K = 10 # Number of *individual messages* (user or AI) to keep in the immediate buffer.

# Threshold for triggering summarization.
# If total messages in history (JSONB) exceed this, we summarize older parts.
# Should be greater than SLIDING_WINDOW_K. E.g., if K=10, trigger at 20-25.
SUMMARY_TRIGGER_THRESHOLD = SLIDING_WINDOW_K * 2 # e.g., 20 messages. Summarize if history exceeds this.

# Other configurations can go here (e.g., API keys, external service URLs, etc.)
# OLLAMA_API_BASE_URL = os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434")