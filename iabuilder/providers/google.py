"""Google provider implementation.

This module implements the ModelProvider interface for Google's Gemini API.
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


class GoogleProvider(ModelProvider):
    """Google Gemini API provider implementation.

    Supports Gemini 2.0 Flash, 1.5 Pro, 1.5 Flash, and other Gemini models.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", **kwargs):
        """Initialize Google provider.

        Args:
            api_key: Google API key (format: AIzaSyXXXX)
            model: Default model to use
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model, **kwargs)

        # Validate API key format
        if not self.validate_api_key():
            print(
                f"Warning: API key '{api_key[:10]}...' appears to be invalid. "
                "Google API keys typically start with 'AIzaSy'."
            )

        # API configuration
        self.base_url = kwargs.get(
            "base_url",
            "https://generativelanguage.googleapis.com"
        )
        self.timeout = kwargs.get("timeout", 30)
        self._available_models: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "google"
        """
        return "google"

    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        if not self.api_key or not self.api_key.strip():
            return False

        # Google API keys start with AIzaSy
        return self.api_key.startswith("AIzaSy")

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from Google Gemini API.

        Uses the OpenAI-compatible endpoint for model listing.

        Returns:
            List of model dictionaries with metadata

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit exceeded
            APIError: If API call fails
        """
        try:
            # Use OpenAI-compatible endpoint
            openai_base = "https://generativelanguage.googleapis.com/v1beta/openai"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{openai_base}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=self.timeout,
                )

                if response.status_code == 401 or response.status_code == 403:
                    raise AuthenticationError("Invalid API key")
                elif response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status_code != 200:
                    raise APIError(f"API error: {response.status_code} - {response.text}")

                data = response.json()
                models = []

                # OpenAI-compatible format: {"data": [{"id": "...", ...}]}
                for model in data.get("data", []):
                    model_id = model.get("id", "")

                    # Extract model name from full path (e.g., "models/gemini-2.5-flash" -> "gemini-2.5-flash")
                    if "/" in model_id:
                        model_id = model_id.split("/")[-1]

                    # Filter to only include generative gemini models
                    if self._is_generative_model(model_id):
                        models.append({
                            "id": model_id,
                            "name": self._get_display_name(model_id),
                            "description": self._get_model_description(model_id),
                            "context_length": self._get_context_length(model_id),
                            "supports_function_calling": self._supports_function_calling_static(model_id),
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
            Hardcoded list of common Gemini models for OpenAI-compatible API
        """
        return [
            {
                "id": "gemini-2.5-flash",
                "name": "Gemini 2.5 Flash",
                "context_length": 1000000,
                "supports_function_calling": True,
                "description": "Latest Gemini 2.5 Flash - fast and capable",
            },
            {
                "id": "gemini-2.5-pro",
                "name": "Gemini 2.5 Pro",
                "context_length": 1000000,
                "supports_function_calling": True,
                "description": "Gemini 2.5 Pro - most capable model",
            },
            {
                "id": "gemini-2.0-flash",
                "name": "Gemini 2.0 Flash",
                "context_length": 1000000,
                "supports_function_calling": True,
                "description": "Gemini 2.0 Flash with multimodal capabilities",
            },
            {
                "id": "gemini-2.0-flash-exp",
                "name": "Gemini 2.0 Flash Exp",
                "context_length": 1000000,
                "supports_function_calling": True,
                "description": "Experimental Gemini 2.0 Flash",
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
        """Send chat completion request to Google Gemini API.

        Args:
            messages: List of message dictionaries with role and content
            model: Model to use (defaults to self.model)
            tools: Optional list of tool/function definitions
            tool_choice: Tool choice mode (not used by Gemini)
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

        # Convert messages to Gemini format
        # Gemini uses "user" and "model" roles instead of "user" and "assistant"
        gemini_contents = []
        system_instruction = None

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "assistant":
                gemini_contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
            elif role == "user":
                gemini_contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })

        # Build request payload
        payload = {
            "contents": gemini_contents,
        }

        # Add generation config
        generation_config = {
            "temperature": temperature,
        }

        if max_tokens:
            generation_config["maxOutputTokens"] = max_tokens

        payload["generationConfig"] = generation_config

        # Add system instruction if present
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        # Convert OpenAI-style tools to Gemini format
        if tools:
            gemini_tools = []
            function_declarations = []

            for tool in tools:
                if tool.get("type") == "function":
                    func = tool.get("function", {})
                    function_declarations.append({
                        "name": func.get("name"),
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {}),
                    })

            if function_declarations:
                gemini_tools.append({
                    "functionDeclarations": function_declarations
                })
                payload["tools"] = gemini_tools

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Choose endpoint based on streaming
                if stream:
                    endpoint = f"{self.base_url}/v1/models/{use_model}:streamGenerateContent"
                else:
                    endpoint = f"{self.base_url}/v1/models/{use_model}:generateContent"

                params = {"key": self.api_key}

                if stream:
                    # Streaming request
                    async with client.stream(
                        "POST",
                        endpoint,
                        params=params,
                        json=payload,
                    ) as response:
                        if response.status_code == 401 or response.status_code == 403:
                            raise AuthenticationError("Invalid API key")
                        elif response.status_code == 429:
                            raise RateLimitError("Rate limit exceeded")
                        elif response.status_code != 200:
                            text = await response.aread()
                            raise APIError(f"API error: {response.status_code} - {text.decode()}")

                        full_content = ""
                        async for line in response.aiter_lines():
                            if line.strip():
                                try:
                                    import json
                                    # Gemini returns JSON objects, not SSE format
                                    chunk = json.loads(line)

                                    # Extract text from candidates
                                    candidates = chunk.get("candidates", [])
                                    if candidates:
                                        parts = candidates[0].get("content", {}).get("parts", [])
                                        for part in parts:
                                            text = part.get("text", "")
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
                        endpoint,
                        params=params,
                        json=payload,
                    )

                    if response.status_code == 401 or response.status_code == 403:
                        raise AuthenticationError("Invalid API key")
                    elif response.status_code == 429:
                        raise RateLimitError("Rate limit exceeded")
                    elif response.status_code != 200:
                        raise APIError(f"API error: {response.status_code} - {response.text}")

                    result = response.json()

                    # Convert Gemini response to OpenAI-compatible format
                    candidates = result.get("candidates", [])
                    if not candidates:
                        raise APIError("No candidates in response")

                    candidate = candidates[0]
                    content_parts = candidate.get("content", {}).get("parts", [])

                    # Extract text and function calls
                    text_content = ""
                    tool_calls = []

                    for part in content_parts:
                        if "text" in part:
                            text_content += part["text"]
                        elif "functionCall" in part:
                            func_call = part["functionCall"]
                            tool_calls.append({
                                "id": f"call_{len(tool_calls)}",
                                "type": "function",
                                "function": {
                                    "name": func_call.get("name"),
                                    "arguments": func_call.get("args", {})
                                }
                            })

                    # Build OpenAI-compatible response
                    message = {
                        "role": "assistant",
                        "content": text_content,
                    }

                    if tool_calls:
                        message["tool_calls"] = tool_calls

                    finish_reason = candidate.get("finishReason", "STOP").lower()
                    if finish_reason == "stop":
                        finish_reason = "stop"
                    elif finish_reason == "max_tokens":
                        finish_reason = "length"

                    return {
                        "choices": [{
                            "message": message,
                            "finish_reason": finish_reason
                        }],
                        "model": use_model,
                        "usage": result.get("usageMetadata", {}),
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
            "embedding": [],
            "other": [],
        }

        for model in models:
            model_id = model["id"]
            lower_id = model_id.lower()

            if "embedding" in lower_id:
                categories["embedding"].append(model_id)
            elif "gemini" in lower_id:
                categories["llm"].append(model_id)
                # All Gemini models support vision
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

        # Gemini 1.5+ models support function calling
        return "gemini-1.5" in lower_id or "gemini-2" in lower_id or "gemini-pro" in lower_id

    def _is_generative_model(self, model_id: str) -> bool:
        """Check if a model is a generative model.

        Args:
            model_id: Model identifier

        Returns:
            True if model is a generative model
        """
        lower_id = model_id.lower()

        # Include Gemini models, exclude embedding models
        return "gemini" in lower_id and "embedding" not in lower_id

    def _get_display_name(self, model_id: str) -> str:
        """Get display name for a model.

        Args:
            model_id: Model identifier

        Returns:
            Human-readable display name
        """
        # Map common model IDs to display names
        display_names = {
            "gemini-2.0-flash-exp": "Gemini 2.0 Flash",
            "gemini-1.5-pro": "Gemini 1.5 Pro",
            "gemini-1.5-flash": "Gemini 1.5 Flash",
            "gemini-1.5-flash-8b": "Gemini 1.5 Flash 8B",
            "gemini-pro": "Gemini Pro",
            "gemini-pro-vision": "Gemini Pro Vision",
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
        if "gemini-1.5-pro" in lower_id:
            return 2000000  # 2M tokens
        elif "gemini-1.5-flash" in lower_id or "gemini-2" in lower_id:
            return 1000000  # 1M tokens
        elif "gemini-pro" in lower_id:
            return 32760

        # Default
        return 32760

    def _get_model_description(self, model_id: str) -> str:
        """Get description for a model.

        Args:
            model_id: Model identifier

        Returns:
            Model description
        """
        lower_id = model_id.lower()

        if "gemini-2" in lower_id:
            return "Google's latest Gemini 2.0 model with enhanced capabilities"
        elif "gemini-1.5-pro" in lower_id:
            return "Most capable Gemini model with extended context window"
        elif "gemini-1.5-flash" in lower_id:
            return "Fast and efficient Gemini model"
        elif "gemini-pro" in lower_id:
            return "Google's Gemini Pro model"

        return f"Google Gemini model: {model_id}"
