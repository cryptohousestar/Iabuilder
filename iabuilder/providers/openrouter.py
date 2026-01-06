"""OpenRouter provider implementation.

This module implements the ModelProvider interface for OpenRouter's API.
OpenRouter is an aggregator that provides access to 100+ models from various providers.
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


class OpenRouterProvider(ModelProvider):
    """OpenRouter API provider implementation.

    OpenRouter provides access to models from OpenAI, Anthropic, Google, Meta,
    Mistral, and many other providers through a unified OpenAI-compatible API.
    """

    def __init__(self, api_key: str, model: str = "anthropic/claude-sonnet-4-5", **kwargs):
        """Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key (format: sk-or-v1-xxx)
            model: Default model to use
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model, **kwargs)

        # Validate API key format
        if not self.validate_api_key():
            print(
                f"Warning: API key '{api_key[:15]}...' appears to be invalid. "
                "OpenRouter API keys typically start with 'sk-or-v1-'."
            )

        # API configuration
        self.base_url = kwargs.get("base_url", "https://openrouter.ai/api/v1")
        self.timeout = kwargs.get("timeout", 60)
        self.site_url = kwargs.get("site_url", "")
        self.app_name = kwargs.get("app_name", "IABuilder")
        self._available_models: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "openrouter"
        """
        return "openrouter"

    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        if not self.api_key or not self.api_key.strip():
            return False

        # OpenRouter keys start with sk-or-v1-
        return self.api_key.startswith("sk-or-v1-") or self.api_key.startswith("sk-or-")

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from OpenRouter API.

        Uses /models/user endpoint to filter by user provider preferences,
        showing only models available/enabled for the authenticated account.

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
                    f"{self.base_url}/models/user",  # Use user-filtered endpoint
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
                    pricing = model.get("pricing", {})

                    # Check if model is free (has :free suffix or $0 pricing)
                    is_free = (
                        ":free" in model_id.lower() or
                        self._is_free_pricing(pricing)
                    )

                    models.append({
                        "id": model_id,
                        "name": model.get("name", model_id),
                        "description": model.get("description", ""),
                        "context_length": model.get("context_length", 4096),
                        "supports_function_calling": self._supports_function_calling_static(model_id),
                        "pricing": pricing,
                        "top_provider": model.get("top_provider", {}),
                        "architecture": model.get("architecture", {}),
                        "is_free": is_free,
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
            Hardcoded list of popular OpenRouter models
        """
        return [
            {
                "id": "anthropic/claude-sonnet-4-5",
                "name": "Claude Sonnet 4.5",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Anthropic's Claude Sonnet 4.5 via OpenRouter",
            },
            {
                "id": "anthropic/claude-opus-4-5",
                "name": "Claude Opus 4.5",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Anthropic's Claude Opus 4.5 via OpenRouter",
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "OpenAI's GPT-4o via OpenRouter",
            },
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o Mini",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "OpenAI's GPT-4o Mini via OpenRouter",
            },
            {
                "id": "google/gemini-2.0-flash-exp",
                "name": "Gemini 2.0 Flash",
                "context_length": 1000000,
                "supports_function_calling": True,
                "description": "Google's Gemini 2.0 Flash via OpenRouter",
            },
            {
                "id": "meta-llama/llama-3.3-70b-instruct",
                "name": "LLaMA 3.3 70B Instruct",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "Meta's LLaMA 3.3 70B via OpenRouter",
            },
            {
                "id": "qwen/qwen-2.5-72b-instruct",
                "name": "Qwen 2.5 72B Instruct",
                "context_length": 32768,
                "supports_function_calling": True,
                "description": "Alibaba's Qwen 2.5 72B via OpenRouter",
            },
            {
                "id": "deepseek/deepseek-chat",
                "name": "DeepSeek Chat",
                "context_length": 64000,
                "supports_function_calling": True,
                "description": "DeepSeek's chat model via OpenRouter",
            },
            {
                "id": "mistralai/mistral-large",
                "name": "Mistral Large",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "Mistral's large model via OpenRouter",
            },
            {
                "id": "x-ai/grok-2-1212",
                "name": "Grok 2",
                "context_length": 131072,
                "supports_function_calling": True,
                "description": "xAI's Grok 2 via OpenRouter",
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
        """Send chat completion request to OpenRouter API.

        OpenRouter uses OpenAI-compatible format, making this implementation
        very similar to OpenAI's.

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

        # OpenRouter-specific headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Optional: Add site URL and app name for OpenRouter analytics
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    # Streaming request
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
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
                        f"{self.base_url}/chat/completions",
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
            "openai": [],
            "anthropic": [],
            "google": [],
            "meta": [],
            "mistral": [],
            "deepseek": [],
            "xai": [],
            "other": [],
        }

        for model in models:
            model_id = model["id"]
            lower_id = model_id.lower()

            # Categorize by provider prefix
            if model_id.startswith("openai/"):
                categories["openai"].append(model_id)
            elif model_id.startswith("anthropic/"):
                categories["anthropic"].append(model_id)
            elif model_id.startswith("google/"):
                categories["google"].append(model_id)
            elif model_id.startswith("meta-llama/"):
                categories["meta"].append(model_id)
            elif model_id.startswith("mistralai/"):
                categories["mistral"].append(model_id)
            elif model_id.startswith("deepseek/"):
                categories["deepseek"].append(model_id)
            elif model_id.startswith("x-ai/"):
                categories["xai"].append(model_id)
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

    def _is_free_pricing(self, pricing: dict) -> bool:
        """Check if pricing indicates a free model.

        Args:
            pricing: Pricing dictionary from OpenRouter API

        Returns:
            True if model is free (prompt and completion cost $0)
        """
        if not pricing:
            return False

        try:
            # OpenRouter returns pricing as strings like "0" or "0.00001"
            prompt_cost = float(pricing.get("prompt", "1"))
            completion_cost = float(pricing.get("completion", "1"))

            # Model is free if both costs are 0
            return prompt_cost == 0 and completion_cost == 0
        except (ValueError, TypeError):
            return False

    def _supports_function_calling_static(self, model_id: str) -> bool:
        """Check if a model supports function calling (static check).

        Args:
            model_id: Model identifier

        Returns:
            True if model likely supports function calling
        """
        lower_id = model_id.lower()

        # Most modern models on OpenRouter support function calling
        # Check for known models that support it
        function_calling_patterns = [
            "gpt-4",
            "gpt-3.5",
            "claude-3",
            "claude-4",
            "gemini-1.5",
            "gemini-2",
            "llama-3",
            "qwen-2",
            "mistral",
            "deepseek",
            "grok",
        ]

        return any(pattern in lower_id for pattern in function_calling_patterns)

    def _get_context_length(self, model_id: str) -> int:
        """Get context length for a model.

        Args:
            model_id: Model identifier

        Returns:
            Context length in tokens
        """
        # This is handled by the API response, but provide defaults
        lower_id = model_id.lower()

        if "claude" in lower_id:
            return 200000
        elif "gpt-4" in lower_id:
            return 128000
        elif "gemini-2" in lower_id or "gemini-1.5" in lower_id:
            return 1000000
        elif "llama-3" in lower_id:
            return 128000

        # Default
        return 4096

    def _get_model_description(self, model_id: str) -> str:
        """Get description for a model.

        Args:
            model_id: Model identifier

        Returns:
            Model description
        """
        # Extract provider and model name
        if "/" in model_id:
            provider, model_name = model_id.split("/", 1)
            return f"{model_name} via OpenRouter ({provider})"

        return f"OpenRouter model: {model_id}"
