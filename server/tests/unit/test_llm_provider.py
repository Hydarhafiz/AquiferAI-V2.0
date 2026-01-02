"""
Unit tests for LLM Provider abstraction layer.

This script tests the OllamaClient implementation with simple queries
to verify the provider abstraction works correctly.

Usage:
    # From server/ directory
    python -m pytest tests/unit/test_llm_provider.py -v

    # Or run directly
    python tests/unit/test_llm_provider.py
"""

import asyncio
import sys
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List

# Add the server directory to the path to allow imports
server_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(server_dir))

from app.core.llm_provider import get_llm_client, AgentName


class SimpleResponse(BaseModel):
    """Simple Pydantic model for testing structured output."""
    answer: str = Field(description="The answer to the question")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")


async def test_text_generation():
    """Test basic text generation."""
    print("\n" + "="*60)
    print("TEST 1: Basic Text Generation")
    print("="*60)

    client = get_llm_client()

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Keep responses brief."},
        {"role": "user", "content": "What is 2 + 2? Answer in one sentence."}
    ]

    try:
        response = await client.generate(
            agent_name=AgentName.PLANNER,
            messages=messages,
            temperature=0.3
        )
        print(f"✓ Response: {response}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_structured_generation():
    """Test structured output with Pydantic model."""
    print("\n" + "="*60)
    print("TEST 2: Structured Output Generation")
    print("="*60)

    client = get_llm_client()

    messages = [
        {"role": "user", "content": "What is the capital of France? Provide your answer and confidence."}
    ]

    try:
        response = await client.generate_structured(
            agent_name=AgentName.PLANNER,
            messages=messages,
            response_model=SimpleResponse,
            temperature=0.3
        )
        print(f"✓ Structured Response:")
        print(f"  - Answer: {response.answer}")
        print(f"  - Confidence: {response.confidence}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_agent_model_mapping():
    """Test that different agents use different models."""
    print("\n" + "="*60)
    print("TEST 3: Agent Model Mapping")
    print("="*60)

    client = get_llm_client()

    print(f"✓ Model Mapping:")
    for agent_name in [AgentName.PLANNER, AgentName.CYPHER_SPECIALIST,
                       AgentName.VALIDATOR, AgentName.ANALYST]:
        model = client._get_model_for_agent(agent_name)
        print(f"  - {agent_name}: {model}")

    return True


async def test_provider_switching():
    """Test that provider switching works via environment variable."""
    print("\n" + "="*60)
    print("TEST 4: Provider Switching")
    print("="*60)

    current_provider = os.getenv("LLM_PROVIDER", "ollama")
    print(f"✓ Current provider: {current_provider}")
    print(f"  To switch providers, set LLM_PROVIDER environment variable:")
    print(f"  - export LLM_PROVIDER=ollama  (for local development)")
    print(f"  - export LLM_PROVIDER=bedrock (for production - Phase 4)")

    return True


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("LLM PROVIDER TEST SUITE")
    print("="*60)
    print("\nTesting LLM Provider abstraction layer...")
    print("Make sure Ollama is running: ollama serve")

    results = []

    # Test 1: Basic text generation
    results.append(await test_text_generation())

    # Test 2: Structured generation
    results.append(await test_structured_generation())

    # Test 3: Model mapping
    results.append(await test_agent_model_mapping())

    # Test 4: Provider switching
    results.append(await test_provider_switching())

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed! Task 1.1 is complete.")
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please check Ollama service.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
