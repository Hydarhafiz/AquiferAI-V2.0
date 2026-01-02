#!/bin/bash

# Setup script for Ollama models required for AquiferAI V2.0 Phase 1
# This script pulls all required models for the multi-agent system

set -e

echo "========================================"
echo "AquiferAI V2.0 - Ollama Setup"
echo "========================================"
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed."
    echo "Please install Ollama from: https://ollama.ai"
    exit 1
fi

echo "✓ Ollama is installed"
echo ""

# Check if Ollama server is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "⚠️  Ollama server is not running."
    echo "Starting Ollama server in background..."
    ollama serve &
    OLLAMA_PID=$!
    echo "Ollama server started with PID: $OLLAMA_PID"
    sleep 3
else
    echo "✓ Ollama server is running"
fi

echo ""
echo "========================================"
echo "Pulling Required Models"
echo "========================================"
echo ""

# Model 1: llama3.2:3b (Planner & Validator)
echo "1/3 Pulling llama3.2:3b (~2GB) for Planner & Validator agents..."
ollama pull llama3.2:3b

echo ""

# Model 2: qwen2.5-coder:7b (Cypher Specialist)
echo "2/3 Pulling qwen2.5-coder:7b (~4.7GB) for Cypher Specialist agent..."
ollama pull qwen2.5-coder:7b

echo ""

# Model 3: llama3:8b (Analyst)
echo "3/3 Pulling llama3:8b (~4.7GB) for Analyst agent..."
ollama pull llama3:8b

echo ""
echo "========================================"
echo "Installed Models"
echo "========================================"
ollama list

echo ""
echo "✅ All models installed successfully!"
echo ""
echo "Agent → Model Mapping:"
echo "  - Planner:          llama3.2:3b (fast, lightweight)"
echo "  - Cypher Specialist: qwen2.5-coder:7b (best for code)"
echo "  - Validator:        llama3.2:3b (fast, lightweight)"
echo "  - Analyst:          llama3:8b (good reasoning)"
echo ""
echo "Total disk space: ~11.4GB"
echo ""
echo "Next steps:"
echo "  1. Run: python test_llm_provider.py"
echo "  2. If tests pass, proceed to Task 1.2 (LangGraph State & Workflow)"
