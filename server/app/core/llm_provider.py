"""
LLM Provider Abstraction Layer

This module provides a unified interface for interacting with different LLM providers.
Supports switching between Ollama (local development) and AWS Bedrock (production)
via the LLM_PROVIDER environment variable.

Usage:
    client = get_llm_client()
    response = await client.generate(agent_name="planner", messages=[...])
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type, TypeVar
from functools import lru_cache
from enum import Enum

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)


class AgentName(str, Enum):
    """Enumeration of agent names for model mapping."""
    PLANNER = "planner"
    CYPHER_SPECIALIST = "cypher-specialist"
    VALIDATOR = "validator"
    ANALYST = "analyst"


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.

    All LLM providers must implement this interface to ensure consistent
    behavior across different backends.
    """

    def __init__(self):
        self.model_mapping: Dict[str, str] = {}
        self._setup_model_mapping()

    @abstractmethod
    def _setup_model_mapping(self) -> None:
        """Set up the mapping between agent names and model IDs."""
        pass

    @abstractmethod
    async def generate(
        self,
        agent_name: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate a text response from the LLM.

        Args:
            agent_name: Name of the agent (maps to specific model)
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        agent_name: str,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> T:
        """
        Generate a structured response conforming to a Pydantic model.

        Args:
            agent_name: Name of the agent (maps to specific model)
            messages: List of message dicts with 'role' and 'content' keys
            response_model: Pydantic model class for structured output
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Instance of response_model populated with LLM response
        """
        pass

    def _get_model_for_agent(self, agent_name: str) -> str:
        """Get the model ID for a given agent name."""
        model = self.model_mapping.get(agent_name)
        if not model:
            raise ValueError(f"No model mapping found for agent: {agent_name}")
        return model


class OllamaClient(BaseLLMClient):
    """
    Ollama LLM client for local development.

    Uses locally-hosted Ollama models with optimized model selection
    per agent type.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.chat_endpoint = f"{self.base_url}/api/chat"
        super().__init__()
        logger.info(f"Initialized OllamaClient with base URL: {self.base_url}")

    def _setup_model_mapping(self) -> None:
        """Map agents to Ollama models optimized for each task."""
        self.model_mapping = {
            AgentName.PLANNER: os.getenv("PLANNER_MODEL", "llama3.2:3b"),
            AgentName.CYPHER_SPECIALIST: os.getenv("CYPHER_MODEL", "qwen2.5-coder:7b"),
            AgentName.VALIDATOR: os.getenv("VALIDATOR_MODEL", "llama3.2:3b"),
            AgentName.ANALYST: os.getenv("ANALYST_MODEL", "llama3:8b"),
        }
        logger.info(f"Ollama model mapping: {self.model_mapping}")

    async def generate(
        self,
        agent_name: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text response using Ollama."""
        model = self._get_model_for_agent(agent_name)

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": kwargs.get("num_ctx", 8192),
                "top_k": kwargs.get("top_k", 40),
                "top_p": kwargs.get("top_p", 0.9),
                "repeat_penalty": kwargs.get("repeat_penalty", 1.1),
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        logger.debug(f"Calling Ollama with model={model}, messages={len(messages)}")

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                response = await client.post(self.chat_endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "").strip()

                if not content:
                    raise ValueError("Empty response from Ollama")

                return content

            except httpx.TimeoutException as e:
                logger.error(f"Ollama timeout for {agent_name}: {e}")
                raise TimeoutError(f"Ollama service timed out for {agent_name}")
            except httpx.HTTPStatusError as e:
                logger.error(f"Ollama HTTP error for {agent_name}: {e.response.status_code}")
                raise RuntimeError(f"Ollama service error: {e.response.text}")
            except Exception as e:
                logger.error(f"Unexpected error calling Ollama for {agent_name}: {e}")
                raise

    async def generate_structured(
        self,
        agent_name: str,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> T:
        """
        Generate structured response using Ollama's JSON mode.

        Note: Ollama doesn't have native structured output support like Bedrock,
        so we use JSON mode + manual parsing with Pydantic validation.
        """
        model = self._get_model_for_agent(agent_name)

        # Enhance the last user message with JSON schema instruction
        enhanced_messages = messages.copy()
        schema_str = json.dumps(response_model.model_json_schema(), indent=2)

        # Add JSON format instruction to system message or create one
        system_instruction = f"""You must respond with valid JSON matching this exact schema:

{schema_str}

Return ONLY the JSON object, no additional text or markdown formatting."""

        # Check if there's already a system message
        if enhanced_messages and enhanced_messages[0]["role"] == "system":
            enhanced_messages[0]["content"] += f"\n\n{system_instruction}"
        else:
            enhanced_messages.insert(0, {"role": "system", "content": system_instruction})

        payload = {
            "model": model,
            "messages": enhanced_messages,
            "stream": False,
            "format": "json",  # Enable JSON mode
            "options": {
                "temperature": temperature,
                "num_ctx": kwargs.get("num_ctx", 8192),
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        logger.debug(f"Calling Ollama (structured) with model={model}")

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                response = await client.post(self.chat_endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "").strip()

                if not content:
                    raise ValueError("Empty response from Ollama")

                # Parse JSON and validate with Pydantic
                try:
                    json_data = json.loads(content)
                    return response_model.model_validate(json_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from Ollama: {content[:200]}")
                    raise ValueError(f"Invalid JSON response: {e}")
                except Exception as e:
                    logger.error(f"Failed to validate response against {response_model.__name__}: {e}")
                    raise ValueError(f"Response validation failed: {e}")

            except httpx.TimeoutException as e:
                logger.error(f"Ollama timeout for {agent_name}: {e}")
                raise TimeoutError(f"Ollama service timed out for {agent_name}")
            except httpx.HTTPStatusError as e:
                logger.error(f"Ollama HTTP error for {agent_name}: {e.response.status_code}")
                raise RuntimeError(f"Ollama service error: {e.response.text}")


class BedrockClient(BaseLLMClient):
    """
    AWS Bedrock LLM client for production deployment.

    Uses Claude 3.5 models via AWS Bedrock with native structured output support.
    This is a skeleton implementation for Phase 4 deployment.
    """

    def __init__(self, region: Optional[str] = None):
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        # boto3 client will be initialized in Phase 4
        self.bedrock_client = None
        super().__init__()
        logger.info(f"Initialized BedrockClient (skeleton) for region: {self.region}")

    def _setup_model_mapping(self) -> None:
        """Map agents to Claude 3.5 models on Bedrock."""
        self.model_mapping = {
            AgentName.PLANNER: "anthropic.claude-3-5-haiku-20241022-v1:0",
            AgentName.CYPHER_SPECIALIST: "anthropic.claude-3-5-sonnet-20241022-v2:0",
            AgentName.VALIDATOR: "anthropic.claude-3-5-haiku-20241022-v1:0",
            AgentName.ANALYST: "anthropic.claude-3-5-sonnet-20241022-v2:0",
        }
        logger.info(f"Bedrock model mapping: {self.model_mapping}")

    async def generate(
        self,
        agent_name: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text response using AWS Bedrock.

        TODO: Implement in Phase 4 with boto3 and anthropic SDK.
        """
        raise NotImplementedError(
            "BedrockClient.generate() will be implemented in Phase 4. "
            "Use OllamaClient for local development."
        )

    async def generate_structured(
        self,
        agent_name: str,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> T:
        """
        Generate structured response using AWS Bedrock with Claude's native tools.

        TODO: Implement in Phase 4 using the `instructor` library with Bedrock.
        """
        raise NotImplementedError(
            "BedrockClient.generate_structured() will be implemented in Phase 4. "
            "Use OllamaClient for local development."
        )


@lru_cache(maxsize=1)
def get_llm_client() -> BaseLLMClient:
    """
    Factory function to get the appropriate LLM client based on environment.

    Uses LRU cache to ensure singleton pattern - only one client instance
    is created per process.

    Environment Variables:
        LLM_PROVIDER: "ollama" (default) or "bedrock"
        OLLAMA_BASE_URL: URL for Ollama service (default: http://localhost:11434)
        AWS_REGION: AWS region for Bedrock (default: us-east-1)

    Returns:
        Configured LLM client instance

    Raises:
        ValueError: If LLM_PROVIDER is invalid
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "ollama":
        logger.info("Using Ollama LLM provider")
        return OllamaClient()
    elif provider == "bedrock":
        logger.info("Using AWS Bedrock LLM provider")
        return BedrockClient()
    else:
        raise ValueError(
            f"Invalid LLM_PROVIDER: {provider}. Must be 'ollama' or 'bedrock'"
        )
