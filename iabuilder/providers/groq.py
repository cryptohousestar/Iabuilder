"""Groq provider implementation.

This module implements the ModelProvider interface for Groq's API.
"""

from typing import Any, Callable, Dict, Iterator, List, Optional, Union

from groq import Groq
from groq.types.chat import ChatCompletion, ChatCompletionChunk

from .base import (
    APIError,
    AuthenticationError,
    ModelProvider,
    ProviderError,
    RateLimitError,
)


class GroqProvider(ModelProvider):
    """Groq API provider implementation."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile", **kwargs):
        """Initialize Groq provider.

        Args:
            api_key: Groq API key
            model: Default model to use
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model, **kwargs)

        # Validate API key format
        if not self.validate_api_key():
            print(
                f"Warning: API key '{api_key}' appears to be invalid. "
                "Groq API keys typically start with 'gsk_'."
            )

        # Initialize Groq client
        self.client = Groq(api_key=api_key)
        self._available_models: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "groq"
        """
        return "groq"

    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        if not self.api_key or not self.api_key.strip():
            return False
        return self.api_key.startswith("gsk_")

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from Groq API.

        Returns:
            List of model dictionaries with metadata

        Raises:
            APIError: If API call fails
        """
        try:
            response = self.client.models.list()
            models = [
                {
                    "id": model.id,
                    "name": model.id,  # Groq doesn't provide separate display name
                    "object": model.object,
                    "created": model.created,
                    "owned_by": model.owned_by,
                    "context_length": self._get_context_length(model.id),
                    "supports_function_calling": self._supports_function_calling_static(model.id),
                    "description": self._get_model_description(model.id),
                }
                for model in response.data
            ]
            self._available_models = models
            return models
        except Exception as e:
            error_msg = str(e).lower()
            if "auth" in error_msg or "401" in error_msg:
                raise AuthenticationError(f"Authentication failed: {e}")
            elif "rate" in error_msg or "429" in error_msg:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            else:
                raise APIError(f"Failed to list models: {e}")

    def get_fallback_models(self) -> List[Dict[str, Any]]:
        """Get fallback model list (static).

        Returns:
            Hardcoded list of common Groq models
        """
        return [
            {
                "id": "llama-3.3-70b-versatile",
                "name": "LLaMA 3.3 70B Versatile",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "Meta's latest LLaMA model, versatile and powerful",
            },
            {
                "id": "llama-3.1-8b-instant",
                "name": "LLaMA 3.1 8B Instant",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "Fast and efficient smaller model",
            },
            {
                "id": "mixtral-8x7b-32768",
                "name": "Mixtral 8x7B",
                "context_length": 32768,
                "supports_function_calling": True,
                "description": "Mistral's mixture of experts model",
            },
            {
                "id": "gemma2-9b-it",
                "name": "Gemma 2 9B IT",
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
    ) -> Union[ChatCompletion, Iterator[ChatCompletionChunk]]:
        """Send chat completion request to Groq API.

        Args:
            messages: List of message dictionaries
            model: Model to use (defaults to self.model)
            tools: Optional list of tool definitions
            tool_choice: Tool choice mode
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            stream: Whether to stream the response
            callback: Optional callback for streaming
            **kwargs: Additional parameters

        Returns:
            ChatCompletion or stream of ChatCompletionChunk

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            APIError: For other API errors
        """
        use_model = model or self.model

        # Build request parameters
        request_params = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            "timeout": kwargs.get("timeout", 60),  # Match OpenRouter timeout
        }

        if max_tokens:
            request_params["max_tokens"] = max_tokens

        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = tool_choice

        try:
            # Debug output (respects /debug command)
            import sys
            from ..debug import DEBUG_ENABLED
            if DEBUG_ENABLED:
                print(f"[DEBUG GROQ] Request params stream={request_params.get('stream')}, has_tools={bool(tools)}", file=sys.stderr, flush=True)

            response = self.client.chat.completions.create(**request_params)

            if DEBUG_ENABLED:
                print(f"[DEBUG GROQ] Response type after create: {type(response)}", file=sys.stderr, flush=True)

            # Handle streaming - MUST reconstruct response for parsing
            if stream:
                if DEBUG_ENABLED:
                    print(f"[DEBUG GROQ] Entering streaming reconstruction block", file=sys.stderr, flush=True)
                # Accumulate content and tool calls while streaming
                full_content = ""
                accumulated_tool_calls = []
                finish_reason = "stop"

                for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta

                        # Accumulate content
                        if delta and delta.content:
                            full_content += delta.content
                            # Call callback if provided
                            if callback:
                                callback(delta.content)

                        # Accumulate tool calls
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            for tool_call in delta.tool_calls:
                                accumulated_tool_calls.append(tool_call)

                        # Get finish reason
                        if hasattr(chunk.choices[0], 'finish_reason') and chunk.choices[0].finish_reason:
                            finish_reason = chunk.choices[0].finish_reason

                # Reconstruct response object for parsing (like OpenRouter does)
                # This is REQUIRED even without callback, otherwise response is consumed Stream
                from groq.types.chat import ChatCompletion, ChatCompletionMessage
                from groq.types.chat.chat_completion import Choice

                # Create a reconstructed response
                reconstructed_message = ChatCompletionMessage(
                    role="assistant",
                    content=full_content if full_content else None,
                    tool_calls=accumulated_tool_calls if accumulated_tool_calls else None,
                )

                reconstructed_choice = Choice(
                    finish_reason=finish_reason,
                    index=0,
                    message=reconstructed_message,
                )

                # Create reconstructed response
                response = ChatCompletion(
                    id=f"chatcmpl-{use_model}",
                    choices=[reconstructed_choice],
                    created=0,
                    model=use_model,
                    object="chat.completion",
                )

            # Validate non-streaming response
            if not stream:
                if not hasattr(response, "choices") or not response.choices:
                    raise APIError(
                        f"Invalid response from API: missing 'choices'. Got: {response}"
                    )

                message = response.choices[0].message
                if not hasattr(message, "content") and not hasattr(message, "tool_calls"):
                    raise APIError(
                        "Response message has neither content nor tool calls"
                    )

            return response

        except Exception as e:
            error_msg = str(e).lower()

            # Categorize errors
            if "auth" in error_msg or "key" in error_msg or "401" in error_msg:
                raise AuthenticationError(
                    f"Authentication failed. Please check your API key: {e}"
                )
            elif "rate" in error_msg or "429" in error_msg:
                raise RateLimitError(f"Rate limit exceeded: {e}")
            else:
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
            "whisper": [],
            "tts": [],
            "moderation": [],
            "other": [],
        }

        for model in models:
            model_id = model["id"]
            lower_id = model_id.lower()

            if "whisper" in lower_id:
                categories["whisper"].append(model_id)
            elif "tts" in lower_id or "playai" in lower_id:
                categories["tts"].append(model_id)
            elif any(x in lower_id for x in ["guard", "safeguard"]):
                categories["moderation"].append(model_id)
            elif any(
                x in lower_id
                for x in [
                    "llama",
                    "qwen",
                    "gemma",
                    "mixtral",
                    "kimi",
                    "allam",
                    "compound",
                    "gpt",
                ]
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

        Note:
            Based on official Groq documentation (https://console.groq.com/docs/tool-use)
            All models hosted on Groq support tool use except audio/embedding models
        """
        lower_id = model_id.lower()

        # Models that DON'T support function calling
        # (Audio, embeddings, and specialized models)
        if any(x in lower_id for x in ["whisper", "tts", "playai", "guard", "embed", "rerank"]):
            return False

        # All other LLM models support function calling
        # Including: llama, mixtral, gemma, qwen, gpt, kimi, compound, etc.
        return True

    def _get_context_length(self, model_id: str) -> int:
        """Get context length for a model.

        Args:
            model_id: Model identifier

        Returns:
            Context length in tokens

        Note:
            Based on official Groq documentation (https://console.groq.com/docs/models)
            Updated 2025-01-01 with current production specifications
        """
        lower_id = model_id.lower()

        # Kimi K2 has largest context window
        if "kimi" in lower_id:
            return 262144  # 256k tokens

        # Most production models have 131k context
        # This includes: llama-3.3, llama-3.1, llama-4, qwen3, gpt-oss, compound
        if any(x in lower_id for x in [
            "llama-3.3", "llama-3.1", "llama-4",
            "qwen", "gpt-oss", "compound",
            "128e", "16e"  # Llama-4 variants
        ]):
            return 131072  # 128k tokens

        # Legacy models with smaller contexts
        if "32k" in lower_id or "32768" in lower_id or "mixtral" in lower_id:
            return 32768
        elif "8k" in lower_id or "8192" in lower_id:
            return 8192

        # Default for modern Groq models is 131k
        # (Conservative for audio/specialized models)
        if any(x in lower_id for x in ["whisper", "tts", "playai", "guard"]):
            return 8192  # Audio models typically have smaller contexts

        # Default for unknown LLM models
        return 131072

    def _get_model_description(self, model_id: str) -> str:
        """Get description for a model.

        Args:
            model_id: Model identifier

        Returns:
            Model description
        """
        lower_id = model_id.lower()

        if "llama" in lower_id:
            return "Meta's LLaMA model family"
        elif "mixtral" in lower_id:
            return "Mistral's mixture of experts model"
        elif "gemma" in lower_id:
            return "Google's Gemma model"
        elif "qwen" in lower_id:
            return "Alibaba's Qwen model"
        elif "whisper" in lower_id:
            return "OpenAI's Whisper speech recognition"

        return f"Model: {model_id}"
