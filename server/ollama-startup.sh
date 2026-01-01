#!/bin/sh
set -e # Exit immediately if a command exits with a non-zero status.
set -x # Print commands and their arguments as they are executed (for debugging)

echo "Starting Ollama startup script..."

# Start ollama server in the background
ollama serve &
OLLAMA_PID=$! # Store the process ID

echo "Waiting for Ollama daemon to be ready for pulling/listing models..."
# Wait for the local Ollama daemon to be ready
# We'll try up to 60 times (5 minutes total) to give it ample time
ATTEMPTS=0
MAX_ATTEMPTS=60
until curl -f http://localhost:11434/api/tags || [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; do
  echo "Local Ollama daemon not yet ready (attempt $((ATTEMPTS+1))/$MAX_ATTEMPTS), waiting..."
  sleep 5;
  ATTEMPTS=$((ATTEMPTS+1))
done;

if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
  echo "Ollama daemon did not become ready within the timeout. Exiting."
  exit 1 # Exit with error if daemon doesn't start
fi

echo "Local Ollama daemon is ready."

# --- NEW MODEL CHECK LOGIC: Use 'ollama list' to check for installed models ---
if ollama list | grep -q "qwen2.5-coder:7b" && \
   ollama list | grep -q "llama3:8b"; then
  echo "Models qwen2.5-coder:7b and llama3:8b already present and listed by Ollama, skipping pull."
else
  echo "One or more models not found or not listed by Ollama. Pulling them now..."
  ollama pull qwen2.5-coder:7b
  ollama pull llama3:8b
  echo "Models pull attempt completed."
fi
# --- END NEW MODEL CHECK LOGIC ---

# Kill the background ollama serve process if it's still running
# This is important because the 'exec "$@"' below will start a new one
echo "Attempting to terminate background Ollama daemon (PID: $OLLAMA_PID)..."
kill $OLLAMA_PID || true # Use '|| true' to prevent script from exiting if kill fails (e.g., process already gone)
wait $OLLAMA_PID || true # Wait for it to actually terminate
sleep 2 # Give it a moment to clean up
echo "Background Ollama daemon terminated."

echo "Executing main Ollama server command: $@"
# Finally, execute the original Ollama server command (e.g., 'ollama serve')
exec "$@"
