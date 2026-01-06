"""Cohere provider implementation.

This module implements the ModelProvider interface for Cohere's API.
Note: Cohere uses a different API format than OpenAI, requiring custom implementation.
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


class CohereProvider(ModelProvider):
    """Cohere API provider implementation.

    Supports Command R+, Command R, and Command Light models.
    Specialized in RAG (Retrieval-Augmented Generation) and enterprise use cases.

    Note: Cohere uses a different API format than OpenAI.
    """

    def __init__(self, api_key: str, model: str = "command-r-plus", **kwargs):
        """Initialize Cohere provider.

        Args:
            api_key: Cohere API key
            model: Default model to use
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, model, **kwargs)

        # Validate API key format
        if not self.validate_api_key():
            print(
                f"Warning: API key appears to be invalid. "
                "Cohere API keys are typically long alphanumeric strings."
            )

        # API configuration
        self.base_url = kwargs.get("base_url", "https://api.cohere.ai/v1")
        self.timeout = kwargs.get("timeout", 30)
        self._available_models: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "cohere"
        """
        return "cohere"

    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        if not self.api_key or not self.api_key.strip():
            return False

        # Cohere keys are long alphanumeric strings
        return len(self.api_key) > 30

    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from Cohere API.

        Note: Cohere doesn't have a standard models endpoint,
        so we return the fallback list.

        Returns:
            List of model dictionaries with metadata
        """
        # Cohere doesn't expose a models list endpoint like OpenAI
        # Return fallback models
        return self.get_fallback_models()

    def get_fallback_models(self) -> List[Dict[str, Any]]:
        """Get fallback model list (static).

        Returns:
            Hardcoded list of Cohere models
        """
        return [
            {
                "id": "command-r-plus",
                "name": "Command R+",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "Most capable model, excellent for RAG and complex tasks",
            },
            {
                "id": "command-r",
                "name": "Command R",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "Balanced model for general-purpose tasks",
            },
            {
                "id": "command-light",
                "name": "Command Light",
                "context_length": 4096,
                "supports_function_calling": True,
                "description": "Fast and efficient lightweight model",
            },
            {
                "id": "command-r-plus-08-2024",
                "name": "Command R+ (August 2024)",
                "context_length": 128000,
                "supports_function_calling": True,
                "description": "August 2024 version of Command R+",
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
        """Send chat completion request to Cohere API.

        Note: This method converts from OpenAI-style format to Cohere's format.

        Args:
            messages: List of message dictionaries with role and content
            model: Model to use (defaults to self.model)
            tools: Optional list of tool/function definitions
            tool_choice: Tool choice mode (not used by Cohere)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 to 1.0)
            stream: Whether to stream the response
            callback: Optional callback for streaming chunks
            **kwargs: Additional parameters

        Returns:
            Chat completion response (converted to OpenAI-style format)

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            APIError: For other API errors
        """
        use_model = model or self.model

        # Convert OpenAI-style messages to Cohere format
        cohere_payload = self._convert_messages_to_cohere_format(messages)

        # Add model and other parameters
        cohere_payload["model"] = use_model
        cohere_payload["temperature"] = temperature
        cohere_payload["stream"] = stream

        if max_tokens:
            cohere_payload["max_tokens"] = max_tokens

        # Convert tools to Cohere format if provided
        if tools:
            cohere_payload["tools"] = self._convert_tools_to_cohere_format(tools)

        # Add Cohere-specific parameters
        if "preamble" in kwargs:
            cohere_payload["preamble"] = kwargs["preamble"]
        if "documents" in kwargs:
            cohere_payload["documents"] = kwargs["documents"]
        if "search_queries_only" in kwargs:
            cohere_payload["search_queries_only"] = kwargs["search_queries_only"]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    # Streaming request
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=cohere_payload,
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
                            if not line:
                                continue

                            try:
                                import json
                                chunk = json.loads(line)

                                # Cohere streaming format
                                event_type = chunk.get("event_type", "")

                                if event_type == "text-generation":
                                    content = chunk.get("text", "")
                                    if content and callback:
                                        callback(content)
                                    full_content += content
                                elif event_type == "stream-end":
                                    break

                            except json.JSONDecodeError:
                                continue

                        # Return in OpenAI-compatible format
                        return {
                            "choices": [{"message": {"content": full_content, "role": "assistant"}}],
                            "model": use_model,
                        }
                else:
                    # Non-streaming request
                    response = await client.post(
                        f"{self.base_url}/chat",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=cohere_payload,
                    )

                    if response.status_code == 401:
                        raise AuthenticationError("Invalid API key")
                    elif response.status_code == 429:
                        raise RateLimitError("Rate limit exceeded")
                    elif response.status_code != 200:
                        raise APIError(f"API error: {response.status_code} - {response.text}")

                    result = response.json()

                    # Convert Cohere response to OpenAI format
                    return self._convert_cohere_response_to_openai_format(result, use_model)

        except (AuthenticationError, RateLimitError, APIError):
            raise
        except Exception as e:
            raise APIError(f"API request failed: {e}")

    def categorize_models(self) -> Dict[str, List[str]]:
        """Categorize available models by type.

        Returns:
            Dictionary mapping category names to model IDs
        """
        models = self.get_fallback_models()

        categories = {
            "llm": [],
            "embedding": [],
            "rerank": [],
            "other": [],
        }

        for model in models:
            model_id = model["id"]
            lower_id = model_id.lower()

            if "embed" in lower_id:
                categories["embedding"].append(model_id)
            elif "rerank" in lower_id:
                categories["rerank"].append(model_id)
            elif "command" in lower_id:
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

        # Command models support function calling (tools)
        # Embed and rerank models do not
        if any(x in lower_id for x in ["embed", "rerank"]):
            return False

        return "command" in lower_id

    def _convert_messages_to_cohere_format(
        self, messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Convert OpenAI-style messages to Cohere format.

        Cohere uses: message (string), chat_history (list of messages), preamble

        Args:
            messages: OpenAI-style messages

        Returns:
            Cohere-formatted payload
        """
        payload = {}
        chat_history = []
        current_message = ""
        preamble = ""

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                # System messages become preamble in Cohere
                preamble += content + "\n"
            elif role == "user":
                # Last user message becomes the main message
                # Previous messages go to chat_history
                if current_message:
                    chat_history.append({"role": "USER", "message": current_message})
                current_message = content
            elif role == "assistant":
                # Assistant messages go to chat_history
                chat_history.append({"role": "CHATBOT", "message": content})

        # Set the current message as the main message
        payload["message"] = current_message or "Hello"

        if chat_history:
            payload["chat_history"] = chat_history

        if preamble:
            payload["preamble"] = preamble.strip()

        return payload

    def _convert_tools_to_cohere_format(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert OpenAI-style tools to Cohere format.

        Args:
            tools: OpenAI-style tool definitions

        Returns:
            Cohere-formatted tool definitions
        """
        cohere_tools = []

        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                cohere_tool = {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "parameter_definitions": {}
                }

                # Convert parameters
                params = func.get("parameters", {})
                properties = params.get("properties", {})
                required = params.get("required", [])

                for param_name, param_info in properties.items():
                    cohere_tool["parameter_definitions"][param_name] = {
                        "description": param_info.get("description", ""),
                        "type": param_info.get("type", "string"),
                        "required": param_name in required,
                    }

                cohere_tools.append(cohere_tool)

        return cohere_tools

    def _convert_cohere_response_to_openai_format(
        self, cohere_response: Dict[str, Any], model: str
    ) -> Dict[str, Any]:
        """Convert Cohere response to OpenAI format.

        Args:
            cohere_response: Response from Cohere API
            model: Model name used

        Returns:
            OpenAI-formatted response
        """
        # Extract text from Cohere response
        text = cohere_response.get("text", "")

        # Check for tool calls
        tool_calls = cohere_response.get("tool_calls", [])

        # Build OpenAI-compatible response
        message = {
            "role": "assistant",
            "content": text,
        }

        # Add tool calls if present
        if tool_calls:
            message["tool_calls"] = [
                {
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": tc.get("name", ""),
                        "arguments": tc.get("parameters", {}),
                    },
                }
                for i, tc in enumerate(tool_calls)
            ]

        return {
            "id": cohere_response.get("generation_id", ""),
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "stop",
                }
            ],
        }

    def _get_display_name(self, model_id: str) -> str:
        """Get display name for a model.

        Args:
            model_id: Model identifier

        Returns:
            Human-readable display name
        """
        display_names = {
            "command-r-plus": "Command R+",
            "command-r": "Command R",
            "command-light": "Command Light",
            "command-r-plus-08-2024": "Command R+ (August 2024)",
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

        if "command-r-plus" in lower_id or "command-r" in lower_id:
            return 128000
        elif "command-light" in lower_id:
            return 4096

        return 4096

    def _get_model_description(self, model_id: str) -> str:
        """Get description for a model.

        Args:
            model_id: Model identifier

        Returns:
            Model description
        """
        lower_id = model_id.lower()

        if "command-r-plus" in lower_id:
            return "Cohere's most capable model, excellent for RAG and enterprise use"
        elif "command-r" in lower_id and "plus" not in lower_id:
            return "Balanced model for general-purpose chat and retrieval"
        elif "command-light" in lower_id:
            return "Fast and efficient lightweight model"

        return f"Cohere model: {model_id}"
