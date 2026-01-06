"""Mistral AI provider implementation.

This module implements the ModelProvider interface for Mistral AI's API.
Mistral API is OpenAI-compatible, making integration straightforward.
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


class MistralProvider(ModelProvider):
    """Mistral AI API provider implementation.

    Supports Mistral Large, Mistral Small, Codestral, and Mixtral models.
    API is OpenAI-compatible.
    """

    def __init__(self, api_key: str, model: str = "mistral-large-latest", **kwargs):
        """Initialize Mistral provider.

        Args:
            api_key: Mistral API key
            model: Default model to use
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model, **kwargs)

        # Validate API key format
        if not self.validate_api_key():
            print(
                f"Warning: API key appears to be invalid. "
                "Mistral API keys typically have a specific format."
            )

        # API configuration
        self.base_url = kwargs.get("base_url", "https://api.mistral.ai/v1")
        self.timeout = kwargs.get("timeout", 30)
        self._available_models: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "mistral"
        """
        return "mistral"

    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        if not self.api_key or not self.api_key.strip():
            return False

        # Mistral keys are typically long alphanumeric strings
        return len(self.api_key) > 20

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from Mistral API.

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
                    models.append({
                        "id": model_id,
                        "name": self._get_display_name(model_id),
                        "object": model.get("object", "model"),
                        "created": model.get("created", 0),
                        "owned_by": model.get("owned_by", "mistralai"),
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
            Hardcoded list of common Mistral models
        """
        return [
            {
                "id": "mistral-large-latest",
                "name": "Mistral Large Latest",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "Mistral's most capable model, excellent for complex tasks",
            },
            {
                "id": "mistral-large-2411",
                "name": "Mistral Large 2 (2411)",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "Mistral Large 2 - November 2024 version",
            },
            {
                "id": "mistral-small-latest",
                "name": "Mistral Small Latest",
                "context_length": 32000,
                "supports_function_calling": True,
                "description": "Efficient smaller model, good balance of speed and capability",
            },
            {
                "id": "codestral-latest",
                "name": "Codestral Latest",
                "context_length": 32000,
                "supports_function_calling": True,
                "description": "Specialized for code generation and understanding",
            },
            {
                "id": "open-mixtral-8x7b",
                "name": "Mixtral 8x7B",
                "context_length": 32768,
                "supports_function_calling": True,
                "description": "Open-source mixture of experts model",
            },
            {
                "id": "open-mixtral-8x22b",
                "name": "Mixtral 8x22B",
                "context_length": 64000,
                "supports_function_calling": True,
                "description": "Larger open-source mixture of experts model",
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
        """Send chat completion request to Mistral API.

        Args:
            messages: List of message dictionaries with role and content
            model: Model to use (defaults to self.model)
            tools: Optional list of tool/function definitions
            tool_choice: Tool choice mode ("auto", "none", "any", or specific tool)
            max_tokens: Maximum tokens in response
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

        # Build request payload (OpenAI-compatible)
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

        # Add additional parameters
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "safe_prompt" in kwargs:
            payload["safe_prompt"] = kwargs["safe_prompt"]

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

                        # Return a response object for streaming
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
            "code": [],
            "embedding": [],
            "other": [],
        }

        for model in models:
            model_id = model["id"]
            lower_id = model_id.lower()

            if "codestral" in lower_id:
                categories["code"].append(model_id)
            elif "embed" in lower_id:
                categories["embedding"].append(model_id)
            elif any(x in lower_id for x in ["mistral", "mixtral"]):
                categories["llm"].append(model_id)
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

        # Mistral models generally support function calling
        # Embedding models do not
        if "embed" in lower_id:
            return False

        return any(
            x in lower_id
            for x in ["mistral", "mixtral", "codestral"]
        )

    def _get_display_name(self, model_id: str) -> str:
        """Get display name for a model.

        Args:
            model_id: Model identifier

        Returns:
            Human-readable display name
        """
        # Map common model IDs to display names
        display_names = {
            "mistral-large-latest": "Mistral Large Latest",
            "mistral-large-2411": "Mistral Large 2",
            "mistral-small-latest": "Mistral Small Latest",
            "codestral-latest": "Codestral Latest",
            "open-mixtral-8x7b": "Mixtral 8x7B",
            "open-mixtral-8x22b": "Mixtral 8x22B",
        }

        return display_names.get(model_id, model_id.replace("-", " ").title())

    def _get_context_length(self, model_id: str) -> int:
        """Get context length for a model.

        Args:
            model_id: Model identifier

        Returns:
            Context length in tokens
        """
        lower_id = model_id.lower()

        # Known context lengths
        if "mistral-large" in lower_id:
            return 128000
        elif "8x22b" in lower_id:
            return 64000
        elif any(x in lower_id for x in ["mistral-small", "codestral", "8x7b"]):
            return 32000

        # Conservative default
        return 32000

    def _get_model_description(self, model_id: str) -> str:
        """Get description for a model.

        Args:
            model_id: Model identifier

        Returns:
            Model description
        """
        lower_id = model_id.lower()

        if "mistral-large" in lower_id:
            return "Mistral's most capable model for complex reasoning tasks"
        elif "mistral-small" in lower_id:
            return "Efficient smaller model with good performance"
        elif "codestral" in lower_id:
            return "Specialized model for code generation and understanding"
        elif "mixtral" in lower_id:
            return "Open-source mixture of experts model"

        return f"Mistral model: {model_id}"
