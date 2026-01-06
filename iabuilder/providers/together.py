"""Together AI provider implementation.

This module implements the ModelProvider interface for Together AI's API.
Together provides access to 100+ open-source models with OpenAI-compatible API.
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


class TogetherProvider(ModelProvider):
    """Together AI API provider implementation.

    Supports 100+ open-source models including:
    - Llama 3.1 405B, 70B, 8B
    - Qwen 2.5 (various sizes)
    - DeepSeek V2.5
    - Mixtral models
    - And many more

    API is OpenAI-compatible.
    """

    def __init__(self, api_key: str, model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", **kwargs):
        """Initialize Together provider.

        Args:
            api_key: Together AI API key
            model: Default model to use
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model, **kwargs)

        # Validate API key format
        if not self.validate_api_key():
            print(
                f"Warning: API key appears to be invalid. "
                "Together AI API keys are typically long hex strings."
            )

        # API configuration
        self.base_url = kwargs.get("base_url", "https://api.together.xyz/v1")
        self.timeout = kwargs.get("timeout", 60)  # Longer timeout for large models
        self._available_models: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "together"
        """
        return "together"

    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        if not self.api_key or not self.api_key.strip():
            return False

        # Together keys are long hex strings
        return len(self.api_key) > 30

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from Together AI API.

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

                # Together returns models in "data" array
                for model in data.get("data", []):
                    model_id = model.get("id", "")

                    # Filter to only include chat/instruct models
                    if self._is_chat_model(model_id):
                        models.append({
                            "id": model_id,
                            "name": self._get_display_name(model_id),
                            "object": model.get("object", "model"),
                            "created": model.get("created", 0),
                            "owned_by": model.get("owned_by", "together"),
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
            Hardcoded list of popular Together models
        """
        return [
            {
                "id": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                "name": "Llama 3.1 405B Instruct Turbo",
                "context_length": 130000,
                "supports_function_calling": True,
                "description": "Meta's largest and most capable Llama model",
            },
            {
                "id": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                "name": "Llama 3.1 70B Instruct Turbo",
                "context_length": 130000,
                "supports_function_calling": True,
                "description": "High-performance 70B Llama model with turbo speed",
            },
            {
                "id": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                "name": "Llama 3.1 8B Instruct Turbo",
                "context_length": 130000,
                "supports_function_calling": True,
                "description": "Fast and efficient 8B Llama model",
            },
            {
                "id": "Qwen/Qwen2.5-72B-Instruct-Turbo",
                "name": "Qwen 2.5 72B Instruct Turbo",
                "context_length": 32768,
                "supports_function_calling": True,
                "description": "Alibaba's powerful Qwen model, excellent for coding",
            },
            {
                "id": "deepseek-ai/deepseek-llm-67b-chat",
                "name": "DeepSeek LLM 67B Chat",
                "context_length": 4096,
                "supports_function_calling": True,
                "description": "DeepSeek's large language model optimized for chat",
            },
            {
                "id": "mistralai/Mixtral-8x7B-Instruct-v0.1",
                "name": "Mixtral 8x7B Instruct",
                "context_length": 32768,
                "supports_function_calling": True,
                "description": "Mistral's mixture of experts model",
            },
            {
                "id": "google/gemma-2-27b-it",
                "name": "Gemma 2 27B IT",
                "context_length": 8192,
                "supports_function_calling": True,
                "description": "Google's Gemma 2 instruction-tuned model",
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
        """Send chat completion request to Together AI API.

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

        # Add Together-specific parameters
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            payload["top_k"] = kwargs["top_k"]
        if "repetition_penalty" in kwargs:
            payload["repetition_penalty"] = kwargs["repetition_penalty"]

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
            "vision": [],
            "other": [],
        }

        for model in models:
            model_id = model["id"]
            lower_id = model_id.lower()

            if "embed" in lower_id:
                categories["embedding"].append(model_id)
            elif "vision" in lower_id or "llava" in lower_id:
                categories["vision"].append(model_id)
            elif any(x in lower_id for x in ["code", "codellama", "deepseek-coder", "starcoder"]):
                categories["code"].append(model_id)
            elif any(
                x in lower_id
                for x in ["llama", "qwen", "mistral", "mixtral", "gemma", "deepseek", "yi"]
            ):
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

        # Models that typically don't support function calling
        if any(x in lower_id for x in ["embed", "base", "continue"]):
            return False

        # Instruct/Chat models generally support function calling
        if any(x in lower_id for x in ["instruct", "chat", "turbo"]):
            return True

        # Conservative default for unknown models
        return False

    def _is_chat_model(self, model_id: str) -> bool:
        """Check if a model is a chat/instruct model.

        Args:
            model_id: Model identifier

        Returns:
            True if model is a chat model
        """
        lower_id = model_id.lower()

        # Include chat/instruct models
        chat_patterns = ["instruct", "chat", "turbo", "it"]
        # Exclude non-chat models
        exclude_patterns = ["embed", "base", "continue", "vision"]

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
        # Extract model name from Together's namespace format (org/model-name)
        if "/" in model_id:
            _, name = model_id.split("/", 1)
            # Clean up the name
            name = name.replace("-", " ").replace("_", " ")
            # Capitalize appropriately
            return " ".join(word.capitalize() for word in name.split())

        return model_id

    def _get_context_length(self, model_id: str) -> int:
        """Get context length for a model.

        Args:
            model_id: Model identifier

        Returns:
            Context length in tokens
        """
        lower_id = model_id.lower()

        # Known context lengths for popular models
        if "llama-3.1" in lower_id or "llama-3.3" in lower_id:
            return 130000
        elif "qwen2.5" in lower_id:
            return 32768
        elif "mixtral" in lower_id or "mistral" in lower_id:
            return 32768
        elif "gemma-2" in lower_id:
            return 8192
        elif "deepseek" in lower_id:
            return 4096

        # Conservative default
        return 4096

    def _get_model_description(self, model_id: str) -> str:
        """Get description for a model.

        Args:
            model_id: Model identifier

        Returns:
            Model description
        """
        lower_id = model_id.lower()

        if "llama-3.1-405b" in lower_id:
            return "Meta's largest and most capable open-source model"
        elif "llama-3.1-70b" in lower_id:
            return "High-performance Llama model, excellent for complex tasks"
        elif "llama-3.1-8b" in lower_id:
            return "Fast and efficient smaller Llama model"
        elif "qwen" in lower_id:
            return "Alibaba's Qwen model, strong at coding and reasoning"
        elif "deepseek" in lower_id:
            return "DeepSeek model, optimized for technical tasks"
        elif "mixtral" in lower_id or "mistral" in lower_id:
            return "Mistral's mixture of experts model"
        elif "gemma" in lower_id:
            return "Google's Gemma model"

        return f"Together AI model: {self._get_display_name(model_id)}"
