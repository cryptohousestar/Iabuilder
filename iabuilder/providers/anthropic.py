"""Anthropic provider implementation.

This module implements the ModelProvider interface for Anthropic's Claude API.
"""

from typing import Any, Callable, Dict, Iterator, List, Optional, Union

import httpx

from .base import (
    APIError,
    AuthenticationError,
    ModelProvider,
    ProviderError,
    RateLimitError,
)


class AnthropicProvider(ModelProvider):
    """Anthropic Claude API provider implementation.

    Supports Claude Opus 4.5, Sonnet 3.5, Haiku 3, and other Claude models.
    Note: Anthropic does not provide a /models endpoint, so we use fallback models only.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929", **kwargs):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (format: sk-ant-xxx)
            model: Default model to use
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model, **kwargs)

        # Validate API key format
        if not self.validate_api_key():
            print(
                f"Warning: API key '{api_key[:10]}...' appears to be invalid. "
                "Anthropic API keys typically start with 'sk-ant-'."
            )

        # API configuration
        self.base_url = kwargs.get("base_url", "https://api.anthropic.com/v1")
        self.timeout = kwargs.get("timeout", 60)  # Claude can take longer
        self.anthropic_version = kwargs.get("anthropic_version", "2023-06-01")
        self._available_models: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "anthropic"
        """
        return "anthropic"

    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        if not self.api_key or not self.api_key.strip():
            return False

        # Anthropic keys start with sk-ant-
        return self.api_key.startswith("sk-ant-")

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from Anthropic API.

        Note: Anthropic does not provide a /models endpoint, so this returns
        the fallback model list.

        Returns:
            List of model dictionaries with metadata
        """
        # Anthropic doesn't have a public /models endpoint
        # Return the static fallback list
        models = self.get_fallback_models()
        self._available_models = models
        return models

    def get_fallback_models(self) -> List[Dict[str, Any]]:
        """Get fallback model list (static).

        Returns:
            Hardcoded list of Claude models
        """
        return [
            {
                "id": "claude-opus-4-5-20251101",
                "name": "Claude Opus 4.5",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Most capable Claude model, best for complex tasks",
            },
            {
                "id": "claude-sonnet-4-5-20250929",
                "name": "Claude Sonnet 4.5",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Balanced performance and speed, ideal for most tasks",
            },
            {
                "id": "claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Previous generation Sonnet with excellent capabilities",
            },
            {
                "id": "claude-3-5-haiku-20241022",
                "name": "Claude 3.5 Haiku",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Fast and efficient model for simpler tasks",
            },
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Most capable Claude 3 model",
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Balanced Claude 3 model",
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Fast and efficient Claude 3 model",
            },
        ]

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stream: bool = False,
        callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> Any:
        """Send chat completion request to Anthropic API.

        Args:
            messages: List of message dictionaries with role and content
            model: Model to use (defaults to self.model)
            tools: Optional list of tool/function definitions
            tool_choice: Tool choice mode ("auto", "any", or specific tool)
            max_tokens: Maximum tokens in response (required for Claude)
            temperature: Sampling temperature (0.0 to 1.0)
            stream: Whether to stream the response
            callback: Optional callback for streaming chunks
            **kwargs: Additional parameters

        Returns:
            Chat completion response object

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            APIError: For other API errors
        """
        use_model = model or self.model

        # Claude requires max_tokens, default to 4096 if not provided
        if max_tokens is None:
            max_tokens = 4096

        # Convert messages to Anthropic format
        # Anthropic requires system messages to be separate
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Build request payload
        payload = {
            "model": use_model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        if system_message:
            payload["system"] = system_message

        # Convert OpenAI-style tools to Anthropic format
        if tools:
            anthropic_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool.get("function", {})
                    anthropic_tools.append({
                        "name": func.get("name"),
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {}),
                    })

            if anthropic_tools:
                payload["tools"] = anthropic_tools

                # Convert tool_choice
                if tool_choice == "auto":
                    payload["tool_choice"] = {"type": "auto"}
                elif tool_choice == "any":
                    payload["tool_choice"] = {"type": "any"}
                elif tool_choice != "none":
                    # Specific tool
                    payload["tool_choice"] = {
                        "type": "tool",
                        "name": tool_choice
                    }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": self.anthropic_version,
                    "Content-Type": "application/json",
                }

                if stream:
                    # Streaming request
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/messages",
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status_code == 401:
                            raise AuthenticationError("Invalid API key")
                        elif response.status_code == 429:
                            raise RateLimitError("Rate limit exceeded")
                        elif response.status_code != 200:
                            text = await response.aread()
                            raise APIError(f"API error: {response.status_code} - {text.decode()}")

                        full_content = ""
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]

                                try:
                                    import json
                                    chunk = json.loads(data)

                                    # Handle different event types
                                    event_type = chunk.get("type")

                                    if event_type == "content_block_delta":
                                        delta = chunk.get("delta", {})
                                        if delta.get("type") == "text_delta":
                                            text = delta.get("text", "")
                                            if text and callback:
                                                callback(text)
                                            full_content += text

                                except json.JSONDecodeError:
                                    continue

                        # Return OpenAI-compatible response format
                        return {
                            "choices": [{
                                "message": {
                                    "content": full_content,
                                    "role": "assistant"
                                },
                                "finish_reason": "stop"
                            }],
                            "model": use_model,
                        }
                else:
                    # Non-streaming request
                    response = await client.post(
                        f"{self.base_url}/messages",
                        headers=headers,
                        json=payload,
                    )

                    if response.status_code == 401:
                        raise AuthenticationError("Invalid API key")
                    elif response.status_code == 429:
                        raise RateLimitError("Rate limit exceeded")
                    elif response.status_code != 200:
                        raise APIError(f"API error: {response.status_code} - {response.text}")

                    result = response.json()

                    # Convert Anthropic response to OpenAI-compatible format
                    content = ""
                    tool_calls = []

                    for block in result.get("content", []):
                        if block.get("type") == "text":
                            content += block.get("text", "")
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
                                "id": block.get("id"),
                                "type": "function",
                                "function": {
                                    "name": block.get("name"),
                                    "arguments": block.get("input", {})
                                }
                            })

                    # Build OpenAI-compatible response
                    message = {
                        "role": "assistant",
                        "content": content,
                    }

                    if tool_calls:
                        message["tool_calls"] = tool_calls

                    return {
                        "choices": [{
                            "message": message,
                            "finish_reason": result.get("stop_reason", "stop")
                        }],
                        "model": use_model,
                        "usage": result.get("usage", {}),
                    }

        except (AuthenticationError, RateLimitError, APIError):
            raise
        except Exception as e:
            raise APIError(f"API request failed: {e}")

    def categorize_models(self) -> Dict[str, List[str]]:
        """Categorize available models by type.

        Returns:
            Dictionary mapping category names to model IDs
        """
        # Get models (use cached if available)
        if self._available_models is None:
            import asyncio
            try:
                models = asyncio.run(self.list_available_models())
            except Exception:
                models = self.get_fallback_models()
        else:
            models = self._available_models

        categories = {
            "llm": [],
            "vision": [],
            "other": [],
        }

        for model in models:
            model_id = model["id"]
            lower_id = model_id.lower()

            # All Claude models support vision and are LLMs
            if "claude" in lower_id:
                categories["llm"].append(model_id)
                # Claude 3+ models have vision capabilities
                if "claude-3" in lower_id or "claude-4" in lower_id:
                    categories["vision"].append(model_id)
            else:
                categories["other"].append(model_id)

        return categories

    def supports_function_calling(self, model: Optional[str] = None) -> bool:
        """Check if a model supports function calling.

        Args:
            model: Model to check (defaults to self.model)

        Returns:
            True if model supports function calling
        """
        check_model = model or self.model
        return self._supports_function_calling_static(check_model)

    def _supports_function_calling_static(self, model_id: str) -> bool:
        """Check if a model supports function calling (static check).

        Args:
            model_id: Model identifier

        Returns:
            True if model likely supports function calling
        """
        lower_id = model_id.lower()

        # All Claude 3+ models support function calling (tools)
        return "claude-3" in lower_id or "claude-4" in lower_id

    def _get_context_length(self, model_id: str) -> int:
        """Get context length for a model.

        Args:
            model_id: Model identifier

        Returns:
            Context length in tokens
        """
        # All modern Claude models have 200K context
        return 200000

    def _get_model_description(self, model_id: str) -> str:
        """Get description for a model.

        Args:
            model_id: Model identifier

        Returns:
            Model description
        """
        lower_id = model_id.lower()

        if "opus" in lower_id:
            return "Most capable Claude model for complex reasoning tasks"
        elif "sonnet" in lower_id:
            return "Balanced Claude model with excellent performance"
        elif "haiku" in lower_id:
            return "Fast and efficient Claude model"

        return f"Anthropic Claude model: {model_id}"
