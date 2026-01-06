"""OpenAI provider implementation.

This module implements the ModelProvider interface for OpenAI's API.
"""

import re
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

import httpx

from .base import (
    APIError,
    AuthenticationError,
    ModelProvider,
    ProviderError,
    RateLimitError,
)


class OpenAIProvider(ModelProvider):
    """OpenAI API provider implementation.

    Supports GPT-4, GPT-4 Turbo, GPT-3.5, and other OpenAI models.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o", **kwargs):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (format: sk-proj-xxx or sk-xxx)
            model: Default model to use
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model, **kwargs)

        # Validate API key format
        if not self.validate_api_key():
            print(
                f"Warning: API key '{api_key[:10]}...' appears to be invalid. "
                "OpenAI API keys typically start with 'sk-' or 'sk-proj-'."
            )

        # API configuration
        self.base_url = kwargs.get("base_url", "https://api.openai.com/v1")
        self.timeout = kwargs.get("timeout", 30)
        self._available_models: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "openai"
        """
        return "openai"

    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        if not self.api_key or not self.api_key.strip():
            return False

        # OpenAI keys start with sk- or sk-proj-
        return self.api_key.startswith("sk-")

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from OpenAI API.

        Returns:
            List of model dictionaries with metadata

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit exceeded
            APIError: If API call fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=self.timeout,
                )

                if response.status_code == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status_code != 200:
                    raise APIError(f"API error: {response.status_code} - {response.text}")

                data = response.json()
                models = []

                for model in data.get("data", []):
                    model_id = model.get("id", "")

                    # Filter to only include relevant chat models
                    if self._is_chat_model(model_id):
                        models.append({
                            "id": model_id,
                            "name": self._get_display_name(model_id),
                            "object": model.get("object", "model"),
                            "created": model.get("created", 0),
                            "owned_by": model.get("owned_by", "openai"),
                            "context_length": self._get_context_length(model_id),
                            "supports_function_calling": self._supports_function_calling_static(model_id),
                            "description": self._get_model_description(model_id),
                        })

                self._available_models = models
                return models

        except (AuthenticationError, RateLimitError):
            raise
        except Exception as e:
            raise APIError(f"Failed to list models: {e}")

    def get_fallback_models(self) -> List[Dict[str, Any]]:
        """Get fallback model list (static).

        Returns:
            Hardcoded list of common OpenAI models
        """
        return [
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "OpenAI's latest GPT-4 Omni model, fastest and most capable",
            },
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "Smaller, faster, cheaper GPT-4o variant",
            },
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "High performance GPT-4 with vision capabilities",
            },
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "context_length": 8192,
                "supports_function_calling": True,
                "description": "Original GPT-4 model",
            },
            {
                "id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "context_length": 16385,
                "supports_function_calling": True,
                "description": "Fast and efficient GPT-3.5 model",
            },
            {
                "id": "gpt-3.5-turbo-16k",
                "name": "GPT-3.5 Turbo 16K",
                "context_length": 16385,
                "supports_function_calling": True,
                "description": "GPT-3.5 with extended context window",
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
        """Send chat completion request to OpenAI API.

        Args:
            messages: List of message dictionaries with role and content
            model: Model to use (defaults to self.model)
            tools: Optional list of tool/function definitions
            tool_choice: Tool choice mode ("auto", "none", or specific tool)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 to 2.0)
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

        # Build request payload
        payload = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    # Streaming request
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
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
                                if data == "[DONE]":
                                    break

                                try:
                                    import json
                                    chunk = json.loads(data)
                                    if chunk.get("choices") and len(chunk["choices"]) > 0:
                                        delta = chunk["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content and callback:
                                            callback(content)
                                        full_content += content
                                except json.JSONDecodeError:
                                    continue

                        # Return a mock response object for streaming
                        return {
                            "choices": [{"message": {"content": full_content, "role": "assistant"}}],
                            "model": use_model,
                        }
                else:
                    # Non-streaming request
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )

                    if response.status_code == 401:
                        raise AuthenticationError("Invalid API key")
                    elif response.status_code == 429:
                        raise RateLimitError("Rate limit exceeded")
                    elif response.status_code != 200:
                        raise APIError(f"API error: {response.status_code} - {response.text}")

                    result = response.json()

                    # Validate response
                    if "choices" not in result or not result["choices"]:
                        raise APIError(f"Invalid response: missing 'choices'. Got: {result}")

                    return result

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
            "embedding": [],
            "audio": [],
            "tts": [],
            "other": [],
        }

        for model in models:
            model_id = model["id"]
            lower_id = model_id.lower()

            if "gpt" in lower_id or "davinci" in lower_id or "curie" in lower_id:
                if "vision" in lower_id or model_id in ["gpt-4-turbo", "gpt-4o"]:
                    categories["vision"].append(model_id)
                else:
                    categories["llm"].append(model_id)
            elif "embedding" in lower_id or "ada" in lower_id:
                categories["embedding"].append(model_id)
            elif "whisper" in lower_id:
                categories["audio"].append(model_id)
            elif "tts" in lower_id:
                categories["tts"].append(model_id)
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

        # Models that support function calling
        function_calling_models = [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-3.5-turbo",
        ]

        return any(pattern in lower_id for pattern in function_calling_models)

    def _is_chat_model(self, model_id: str) -> bool:
        """Check if a model is a chat model.

        Args:
            model_id: Model identifier

        Returns:
            True if model is a chat model
        """
        lower_id = model_id.lower()

        # Include GPT models and exclude non-chat models
        chat_patterns = ["gpt-4", "gpt-3.5"]
        exclude_patterns = ["embedding", "whisper", "tts", "dall-e", "davinci"]

        is_chat = any(pattern in lower_id for pattern in chat_patterns)
        is_excluded = any(pattern in lower_id for pattern in exclude_patterns)

        return is_chat and not is_excluded

    def _get_display_name(self, model_id: str) -> str:
        """Get display name for a model.

        Args:
            model_id: Model identifier

        Returns:
            Human-readable display name
        """
        # Map common model IDs to display names
        display_names = {
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-4": "GPT-4",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "gpt-3.5-turbo-16k": "GPT-3.5 Turbo 16K",
        }

        return display_names.get(model_id, model_id)

    def _get_context_length(self, model_id: str) -> int:
        """Get context length for a model.

        Args:
            model_id: Model identifier

        Returns:
            Context length in tokens
        """
        lower_id = model_id.lower()

        # Known context lengths
        if "gpt-4o" in lower_id or "gpt-4-turbo" in lower_id:
            return 128000
        elif "gpt-4-32k" in lower_id:
            return 32768
        elif "gpt-4" in lower_id:
            return 8192
        elif "gpt-3.5-turbo-16k" in lower_id:
            return 16385
        elif "gpt-3.5-turbo" in lower_id:
            return 4096

        # Default
        return 8192

    def _get_model_description(self, model_id: str) -> str:
        """Get description for a model.

        Args:
            model_id: Model identifier

        Returns:
            Model description
        """
        lower_id = model_id.lower()

        if "gpt-4o" in lower_id:
            return "OpenAI's GPT-4 Omni model with multimodal capabilities"
        elif "gpt-4-turbo" in lower_id:
            return "High performance GPT-4 with vision capabilities"
        elif "gpt-4" in lower_id:
            return "OpenAI's most capable GPT-4 model"
        elif "gpt-3.5" in lower_id:
            return "Fast and efficient GPT-3.5 model"

        return f"OpenAI model: {model_id}"
