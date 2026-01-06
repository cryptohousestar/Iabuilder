"""DeepSeek provider implementation.

This module implements the ModelProvider interface for DeepSeek's API.
DeepSeek offers very cost-effective models excellent for code generation.
API is OpenAI-compatible.
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


class DeepSeekProvider(ModelProvider):
    """DeepSeek API provider implementation.

    Supports DeepSeek V3, DeepSeek Coder V2, and other DeepSeek models.
    Known for excellent code generation and very low pricing.
    API is OpenAI-compatible.
    """

    def __init__(self, api_key: str, model: str = "deepseek-chat", **kwargs):
        """Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key
            model: Default model to use
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model, **kwargs)

        # Validate API key format
        if not self.validate_api_key():
            print(
                f"Warning: API key appears to be invalid. "
                "DeepSeek API keys typically start with 'sk-'."
            )

        # API configuration
        self.base_url = kwargs.get("base_url", "https://api.deepseek.com/v1")
        self.timeout = kwargs.get("timeout", 30)
        self._available_models: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "deepseek"
        """
        return "deepseek"

    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        if not self.api_key or not self.api_key.strip():
            return False

        # DeepSeek keys start with sk-
        return self.api_key.startswith("sk-")

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from DeepSeek API.

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
                        "owned_by": model.get("owned_by", "deepseek"),
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
            Hardcoded list of DeepSeek models
        """
        return [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek Chat",
                "context_length": 64000,
                "supports_function_calling": True,
                "description": "DeepSeek V3 - latest chat model, extremely cost-effective",
            },
            {
                "id": "deepseek-coder",
                "name": "DeepSeek Coder",
                "context_length": 64000,
                "supports_function_calling": True,
                "description": "DeepSeek Coder V2 - specialized for code generation",
            },
            {
                "id": "deepseek-reasoner",
                "name": "DeepSeek Reasoner",
                "context_length": 64000,
                "supports_function_calling": True,
                "description": "DeepSeek R1 - advanced reasoning model with chain-of-thought",
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
        """Send chat completion request to DeepSeek API.

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

        # Add DeepSeek-specific parameters
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]

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
            "reasoning": [],
            "other": [],
        }

        for model in models:
            model_id = model["id"]
            lower_id = model_id.lower()

            if "coder" in lower_id:
                categories["code"].append(model_id)
            elif "reason" in lower_id or "r1" in lower_id:
                categories["reasoning"].append(model_id)
            elif "chat" in lower_id or "deepseek" in lower_id:
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

        # DeepSeek chat and coder models support function calling
        return any(
            x in lower_id
            for x in ["chat", "coder", "reasoner", "deepseek"]
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
            "deepseek-chat": "DeepSeek Chat (V3)",
            "deepseek-coder": "DeepSeek Coder (V2)",
            "deepseek-reasoner": "DeepSeek Reasoner (R1)",
        }

        return display_names.get(model_id, model_id.replace("-", " ").title())

    def _get_context_length(self, model_id: str) -> int:
        """Get context length for a model.

        Args:
            model_id: Model identifier

        Returns:
            Context length in tokens
        """
        # DeepSeek V3 and Coder V2 support 64K context
        # Older models had 32K
        lower_id = model_id.lower()

        if any(x in lower_id for x in ["v3", "v2", "chat", "coder", "reasoner"]):
            return 64000

        # Conservative default for unknown/older models
        return 32000

    def _get_model_description(self, model_id: str) -> str:
        """Get description for a model.

        Args:
            model_id: Model identifier

        Returns:
            Model description
        """
        lower_id = model_id.lower()

        if "chat" in lower_id:
            return "DeepSeek V3 - extremely cost-effective chat model, great for general tasks"
        elif "coder" in lower_id:
            return "DeepSeek Coder V2 - specialized for code generation and understanding"
        elif "reason" in lower_id:
            return "DeepSeek R1 - advanced reasoning model with chain-of-thought capabilities"

        return f"DeepSeek model: {model_id}"
