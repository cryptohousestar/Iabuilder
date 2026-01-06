"""AIML API provider implementation.

This module implements the ModelProvider interface for AIML API.
AIML API provides access to multiple models through a unified OpenAI-compatible API.
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


class AIMLProvider(ModelProvider):
    """AIML API provider implementation.

    AIML API provides access to models from OpenAI, Anthropic, Google, Meta,
    and many other providers through a unified OpenAI-compatible API.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o", **kwargs):
        """Initialize AIML provider.

        Args:
            api_key: AIML API key
            model: Default model to use
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model, **kwargs)

        # Validate API key format
        if not self.validate_api_key():
            print(
                f"Warning: API key '{api_key[:15]}...' appears to be invalid. "
                "AIML API keys should be valid UUID format."
            )

        # API configuration
        self.base_url = kwargs.get("base_url", "https://api.aimlapi.com/v1")
        self.timeout = kwargs.get("timeout", 60)
        self.site_url = kwargs.get("site_url", "")
        self.app_name = kwargs.get("app_name", "IABuilder")
        self._available_models: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "aiml"
        """
        return "aiml"

    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        if not self.api_key or not self.api_key.strip():
            return False

        # AIML API keys appear to be UUID format
        # Example: c2b8f4ff4b8b402d9bed465a455ccea8
        api_key = self.api_key.strip()

        # Check length (UUID is typically 32-36 chars)
        if len(api_key) < 20:
            return False

        # Check for valid hex characters (UUID format)
        import string
        valid_chars = string.ascii_lowercase + string.digits + '-'
        return all(c in valid_chars for c in api_key.lower())

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from AIML API.

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
                    info = model.get("info", {})
                    
                    # AIML API doesn't provide explicit pricing in the models endpoint
                    # We need to determine if model is free-tier friendly based on patterns
                    is_free_tier = self._is_free_tier_model(model_id)
                    
                    # Get context length from info if available
                    context_length = info.get("contextLength") or model.get("context_length", 4096)

                    models.append({
                        "id": model_id,
                        "name": info.get("name") or model.get("name", model_id),
                        "description": info.get("description") or model.get("description", ""),
                        "context_length": context_length,
                        "supports_function_calling": self._supports_function_calling_static(model_id),
                        "pricing": {
                            "prompt": 0 if is_free_tier else None,
                            "completion": 0 if is_free_tier else None,
                            "free_tier": is_free_tier,
                        },
                        "architecture": model.get("architecture", {}),
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
            Popular AIML models based on real API data (432+ models available)
        """
        return [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "OpenAI GPT-4o - Multimodal AI with text, vision, and audio",
                "pricing": {"prompt": 0, "completion": 0, "free_tier": True},  # Free tier friendly
            },
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o Mini",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "OpenAI GPT-4o Mini - Fast and efficient",
                "pricing": {"prompt": 0, "completion": 0, "free_tier": True},
            },
            {
                "id": "claude-3-5-haiku-20241022",
                "name": "Claude 3.5 Haiku",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Anthropic Claude 3.5 Haiku via AIML API",
                "pricing": {"prompt": 0, "completion": 0, "free_tier": True},
            },
            {
                "id": "openai/gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "OpenAI GPT-4 Turbo via AIML API",
                "pricing": {"prompt": 0, "completion": 0, "free_tier": True},
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Anthropic Claude 3 Haiku via AIML API",
                "pricing": {"prompt": 0, "completion": 0, "free_tier": True},
            },
            {
                "id": "google/gemini-2.0-flash",
                "name": "Gemini 2.0 Flash",
                "context_length": 1000000,
                "supports_function_calling": True,
                "description": "Google Gemini 2.0 Flash via AIML API",
                "pricing": {"prompt": 0, "completion": 0, "free_tier": True},
            },
            {
                "id": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "name": "LLaMA 3.3 70B Instruct Turbo",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "Meta LLaMA 3.3 70B via AIML API",
                "pricing": {"prompt": 0, "completion": 0, "free_tier": True},
            },
            {
                "id": "deepseek-chat",
                "name": "DeepSeek Chat",
                "context_length": 64000,
                "supports_function_calling": True,
                "description": "DeepSeek Chat model via AIML API",
                "pricing": {"prompt": 0, "completion": 0, "free_tier": True},
            },
            {
                "id": "claude-sonnet-4-5-20250929",
                "name": "Claude Sonnet 4.5",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Anthropic Claude Sonnet 4.5 via AIML API",
                "pricing": {"prompt": None, "completion": None, "free_tier": False},  # Premium model
            },
            {
                "id": "openai/gpt-5-2025-08-07",
                "name": "GPT-5",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "OpenAI GPT-5 via AIML API (latest)",
                "pricing": {"prompt": None, "completion": None, "free_tier": False},  # Premium model
            },
            {
                "id": "claude-opus-4-5-20251101",
                "name": "Claude Opus 4.5",
                "context_length": 200000,
                "supports_function_calling": True,
                "description": "Anthropic Claude Opus 4.5 via AIML API",
                "pricing": {"prompt": None, "completion": None, "free_tier": False},  # Premium model
            },
            {
                "id": "alibaba/qwen-max",
                "name": "Qwen Max",
                "context_length": 32000,
                "supports_function_calling": True,
                "description": "Alibaba Qwen Max via AIML API",
                "pricing": {"prompt": None, "completion": None, "free_tier": False},  # Premium model
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
        """Send chat completion request to AIML API.

        AIML uses OpenAI-compatible format, making this implementation
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

        # Normalize messages for AIML API compatibility
        normalized_messages = self._normalize_messages_for_aiml(messages)

        # Build request payload (OpenAI-compatible)
        payload = {
            "model": use_model,
            "messages": normalized_messages,
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        # AIML-specific headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Optional: Add site URL and app name for AIML analytics
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
        """Categorize available models by provider based on real AIML API data.

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
            "alibaba": [],
            "other": [],
        }

        for model in models:
            model_id = model["id"]
            lower_id = model_id.lower()

            # Categorize by provider prefix
            if model_id.startswith("openai/") or any(prefix in lower_id for prefix in ["gpt-", "o1-", "o3-", "o4-"]):
                categories["openai"].append(model_id)
            elif model_id.startswith("claude-") or model_id.startswith("anthropic/"):
                categories["anthropic"].append(model_id)
            elif model_id.startswith("google/") or "gemini" in lower_id:
                categories["google"].append(model_id)
            elif model_id.startswith("meta-llama/") or "llama" in lower_id:
                categories["meta"].append(model_id)
            elif model_id.startswith("mistralai/") or "mistral" in lower_id:
                categories["mistral"].append(model_id)
            elif "deepseek" in lower_id:
                categories["deepseek"].append(model_id)
            elif model_id.startswith("alibaba/") or "qwen" in lower_id:
                categories["alibaba"].append(model_id)
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
        """Check if a model supports function calling based on real AIML API capabilities.

        Args:
            model_id: Model identifier

        Returns:
            True if model likely supports function calling
        """
        lower_id = model_id.lower()

        # Most modern models on AIML support function calling
        # Based on API features, these models support function calling:
        function_calling_patterns = [
            "gpt-4", "gpt-5", "gpt-3.5",  # OpenAI models
            "claude-3", "claude-4", "claude-sonnet", "claude-opus", "claude-haiku",  # Anthropic models
            "gemini-1.5", "gemini-2",    # Google models
            "llama-3",                   # Meta models
            "qwen",                      # Alibaba models
            "mistral",                   # Mistral models
            "deepseek",                  # DeepSeek models
        ]

        # Exclude models that definitely don't support function calling
        # (mostly older models, audio/video models, etc.)
        excluded_patterns = [
            "whisper", "tts", "audio", "video", "image",
            "music", "stable-audio", "eleven",
            "dall-e", "midjourney", "flux", "sdxl",
            "kling", "runway", "sora", "veo",
        ]

        has_function_calling = any(pattern in lower_id for pattern in function_calling_patterns)
        is_excluded = any(pattern in lower_id for pattern in excluded_patterns)

        return has_function_calling and not is_excluded

    def _get_context_length(self, model_id: str) -> int:
        """Get context length for a model based on real AIML API data.

        Args:
            model_id: Model identifier

        Returns:
            Context length in tokens
        """
        lower_id = model_id.lower()

        # Claude models - high context
        if "claude" in lower_id:
            return 200000

        # GPT-4 and GPT-5 models
        elif "gpt-4" in lower_id or "gpt-5" in lower_id:
            return 128000

        # Gemini models - very high context
        elif "gemini-2" in lower_id or "gemini-1.5" in lower_id:
            return 1000000

        # Llama models
        elif "llama-3.3" in lower_id or "llama-3.2" in lower_id:
            return 128000
        elif "llama-3.1" in lower_id:
            return 128000

        # DeepSeek models
        elif "deepseek" in lower_id:
            return 64000

        # Qwen models
        elif "qwen" in lower_id:
            if "max" in lower_id:
                return 32000
            else:
                return 32000

        # Mistral models
        elif "mistral" in lower_id:
            return 32000

        # Default fallback
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
            return f"{model_name} via AIML API ({provider})"

        return f"AIML model: {model_id}"

    def _is_free_tier_model(self, model_id: str) -> bool:
        """Determine if a model is free-tier friendly based on patterns.

        AIML API provides 50,000 free credits for testing, but some models
        consume credits faster. Models marked as "free-tier" are those that
        are typically available with free credits and don't require paid plans.

        Args:
            model_id: Model identifier

        Returns:
            True if model is suitable for free tier, False if requires paid credits
        """
        lower_id = model_id.lower()

        # Models that are typically FREE TIER (basic/common models)
        free_tier_patterns = [
            # OpenAI basic models
            "gpt-4o-mini",
            "gpt-3.5-turbo",
            "gpt-4o",  # GPT-4o is available with free credits
            "gpt-4-turbo",

            # Claude basic models
            "claude-3-haiku",
            "claude-3-5-haiku",

            # Google basic models
            "gemini-2.0-flash",
            "gemini-1.5-flash",

            # Meta basic models
            "llama-3.1-8b",
            "llama-3.2-3b",
            "llama-3.3-70b",

            # DeepSeek basic
            "deepseek-chat",

            # Mistral basic
            "mistral-7b",
            "mixtral-8x7b",

            # Qwen basic
            "qwen-turbo",
            "qwen2.5-7b",
        ]

        # Models that typically require PAID credits (premium/advanced)
        paid_tier_patterns = [
            # Premium OpenAI models
            "gpt-5",
            "gpt-4.1",
            "o1",
            "o3",
            "o4",

            # Premium Claude models
            "claude-opus",
            "claude-sonnet-4",
            "claude-opus-4",

            # Premium Google models
            "gemini-2.5-pro",
            "gemini-2.0-flash-exp",

            # Premium Meta models
            "llama-3.1-405b",
            "llama-4",

            # Premium Alibaba models
            "qwen-max",
            "qwen-plus",
            "qwen3-235b",
            "qwen3-max",

            # Premium DeepSeek
            "deepseek-reasoner",

            # Video/Audio models (consume more credits)
            "video",
            "audio",
            "sora",
            "veo",
            "kling",
            "runway",
            "music",
            "tts",
        ]

        # Check if it's a paid tier model first (more specific)
        if any(pattern in lower_id for pattern in paid_tier_patterns):
            return False

        # Check if it matches free tier patterns
        if any(pattern in lower_id for pattern in free_tier_patterns):
            return True

        # Default: assume free tier friendly (most models work with free credits)
        # Users can use any model with their 50,000 free credits
        return True

    def _normalize_messages_for_aiml(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize messages for AIML API compatibility.

        AIML API is OpenAI-compatible but has specific requirements:
        - Assistant messages with tool_calls should omit content field when None
        - Tool calls must have proper format validation
        - Tool messages must have string content

        Args:
            messages: Original messages from conversation

        Returns:
            Normalized messages compatible with AIML API
        """
        import json

        normalized = []

        for msg in messages:
            normalized_msg = {"role": msg["role"]}

            # Handle content field
            if "content" in msg:
                content = msg["content"]
                if content is None:
                    # Omit content field completely when None (AIML requirement)
                    pass
                else:
                    # Ensure content is string
                    normalized_msg["content"] = str(content)

            # Handle tool_calls (assistant messages)
            if "tool_calls" in msg and msg["role"] == "assistant":
                tool_calls = []
                for tc in msg["tool_calls"]:
                    # Validate and normalize tool call format
                    if isinstance(tc, dict) and "function" in tc:
                        normalized_tc = {
                            "id": tc.get("id", ""),
                            "type": tc.get("type", "function"),
                            "function": {
                                "name": tc["function"].get("name", ""),
                                "arguments": tc["function"].get("arguments", "{}")
                            }
                        }
                        tool_calls.append(normalized_tc)
                    else:
                        # Try to convert from other formats
                        try:
                            if hasattr(tc, 'model_dump'):
                                tc_dict = tc.model_dump()
                            elif hasattr(tc, 'dict'):
                                tc_dict = tc.dict()
                            else:
                                tc_dict = dict(tc) if hasattr(tc, 'keys') else tc

                            normalized_tc = {
                                "id": tc_dict.get("id", ""),
                                "type": tc_dict.get("type", "function"),
                                "function": {
                                    "name": tc_dict.get("function", {}).get("name", ""),
                                    "arguments": tc_dict.get("function", {}).get("arguments", "{}")
                                }
                            }
                            tool_calls.append(normalized_tc)
                        except Exception:
                            # Skip invalid tool calls
                            continue

                if tool_calls:
                    normalized_msg["tool_calls"] = tool_calls

            # Handle tool messages
            if msg["role"] == "tool":
                # Ensure tool_call_id is present
                if "tool_call_id" in msg:
                    normalized_msg["tool_call_id"] = msg["tool_call_id"]
                elif "id" in msg:  # fallback
                    normalized_msg["tool_call_id"] = msg["id"]

                # Ensure name is present
                if "name" in msg:
                    normalized_msg["name"] = msg["name"]

                # Ensure content is string
                if "content" in msg:
                    content = msg["content"]
                    if isinstance(content, dict):
                        normalized_msg["content"] = json.dumps(content, ensure_ascii=False)
                    else:
                        normalized_msg["content"] = str(content)

            normalized.append(normalized_msg)

        return normalized