"""OpenAI-compatible API client wrapper.

This module provides a wrapper around the OpenAI SDK that matches
the interface of GroqClient, enabling seamless switching between
providers like OpenRouter, OpenAI, and other OpenAI-compatible APIs.
"""

from typing import Any, Callable, Dict, Iterator, List, Optional, Union

from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from .rate_limiter import get_rate_limiter
from .debug import debug, debug_separator, debug_stream_chunk, debug_api_request


class OpenAICompatibleClient:
    """Wrapper for OpenAI-compatible APIs with GroqClient interface.

    This wrapper allows using OpenRouter, OpenAI, and other OpenAI-compatible
    APIs with the same interface as GroqClient.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None
    ):
        """Initialize OpenAI-compatible client.

        Args:
            api_key: API key for the provider
            model: Default model to use
            base_url: Base URL for the API (e.g., https://openrouter.ai/api/v1)
        """
        self.model = model
        self.base_url = base_url
        self.is_openrouter = base_url and "openrouter" in base_url

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        # Add OpenRouter-specific headers
        if self.is_openrouter:
            client_kwargs["default_headers"] = {
                "HTTP-Referer": "https://github.com/iabuilder",
                "X-Title": "IABuilder"
            }

        self.client = OpenAI(**client_kwargs)
        self._available_models: Optional[List[Dict[str, Any]]] = None

    def send_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stream: bool = False,
        callback: Optional[Callable[[str], None]] = None,
    ) -> ChatCompletion:
        """Send a message to the API.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions (function calling)
            tool_choice: Tool choice mode ("auto", "none", or specific tool)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            stream: Whether to stream the response
            callback: Optional callback function for streamed chunks

        Returns:
            ChatCompletion response

        Raises:
            Exception: If there's an error communicating with the API
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            "timeout": 60,
        }

        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        # Debug API request
        debug_separator("api", "API REQUEST")
        debug_api_request(
            self.base_url or "openai",
            self.model,
            len(messages),
            bool(tools)
        )
        debug("api", f"Temperature: {temperature}, Stream: {stream}, MaxTokens: {max_tokens}")

        # Show message roles
        for i, msg in enumerate(messages[-5:]):  # Last 5 messages
            role = msg.get("role", "?")
            content = msg.get("content", "")[:50] if msg.get("content") else "(no content)"
            has_tc = bool(msg.get("tool_calls"))
            debug("api", f"  [{role}]: {content}{'...' if len(msg.get('content', '') or '') > 50 else ''} {'[+tools]' if has_tc else ''}", indent=1)

        # Smart rate limiting
        rate_limiter = get_rate_limiter()
        estimated_tokens = rate_limiter.estimate_tokens(messages, tools)
        debug("api", f"Estimated tokens: {estimated_tokens}")

        try:
            delayed = rate_limiter.smart_delay(estimated_tokens)
            if delayed:
                debug("api", "Rate limit delay applied")
                print("🔄 Continuing after processing...")
        except KeyboardInterrupt:
            print("\n⏹️  Request cancelled by user")
            return self._create_cancelled_response()

        try:
            debug("api", "Calling API...")
            response = self.client.chat.completions.create(**kwargs)

            # Handle streaming response
            if stream:
                return self._handle_streaming_response(response, callback, rate_limiter, estimated_tokens)

            # Record token usage for non-streaming
            if hasattr(response, 'usage') and response.usage:
                tokens_used = getattr(response.usage, 'total_tokens', estimated_tokens)
            else:
                tokens_used = estimated_tokens

            rate_limiter.record_usage(tokens_used)

            # Validate response
            if not hasattr(response, "choices") or not response.choices:
                raise ValueError(
                    f"Invalid response from API: missing 'choices'. Got: {response}"
                )

            return response

        except Exception as e:
            error_str = str(e).lower()

            # Check if it's an authentication error
            if "auth" in error_str or "key" in error_str or "401" in str(e):
                print(
                    "\n⚠️ AUTHENTICATION ERROR: Your API key may be invalid or expired."
                )

            raise

    def _create_cancelled_response(self):
        """Create a response for when request is cancelled."""
        class CancelledResponse:
            def __init__(self):
                self.choices = [self.CancelledChoice()]

            class CancelledChoice:
                def __init__(self):
                    self.message = self.CancelledMessage()

                class CancelledMessage:
                    def __init__(self):
                        self.content = "Request cancelled by user."
                        self.tool_calls = None

        return CancelledResponse()

    def _handle_streaming_response(self, stream_response, callback, rate_limiter, estimated_tokens):
        """Handle streaming response from API.

        Args:
            stream_response: Iterator of ChatCompletionChunk
            callback: Optional callback for each chunk
            rate_limiter: Rate limiter instance
            estimated_tokens: Estimated tokens for rate limiting

        Returns:
            Simulated ChatCompletion with accumulated content
        """
        debug_separator("streaming", "STREAMING RESPONSE")

        full_content = ""
        tool_calls = []
        tool_call_chunks = {}  # Accumulate tool call data
        chunk_count = 0
        content_chunks = 0
        tool_chunks = 0

        try:
            for chunk in stream_response:
                chunk_count += 1

                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # Handle content chunks
                if delta.content:
                    full_content += delta.content
                    content_chunks += 1
                    if callback:
                        callback(delta.content)

                    # Debug first few content chunks
                    if content_chunks <= 3:
                        debug_stream_chunk("content", delta.content[:30])

                # Handle tool call chunks (accumulate them)
                if delta.tool_calls:
                    tool_chunks += 1
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_call_chunks:
                            tool_call_chunks[idx] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            }
                            # Debug new tool call
                            tool_name = tc.function.name if tc.function else "unknown"
                            debug_stream_chunk("tool_start", tool_name=tool_name)

                            # Show visual feedback when a new tool call starts
                            if tc.function and tc.function.name and callback:
                                callback(f"\n🔧 Preparando: {tc.function.name}...")

                        if tc.id:
                            tool_call_chunks[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_call_chunks[idx]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_call_chunks[idx]["function"]["arguments"] += tc.function.arguments
                                # Debug args accumulation (only first few)
                                if tool_chunks <= 5:
                                    debug_stream_chunk("tool_args", tc.function.arguments)

        except KeyboardInterrupt:
            debug("streaming", "User cancelled streaming")
            # Allow cancelling during streaming
            if callback:
                callback("\n[Cancelled]")
            full_content += "\n[Response cancelled by user]"

        # Convert accumulated tool calls to list
        if tool_call_chunks:
            tool_calls = [tool_call_chunks[i] for i in sorted(tool_call_chunks.keys())]

        # Debug summary
        debug_stream_chunk("done")
        debug("streaming", f"Stream complete: {chunk_count} chunks, {content_chunks} content, {tool_chunks} tool")
        debug("streaming", f"Content length: {len(full_content)} chars")
        debug("streaming", f"Tool calls: {len(tool_calls)}")

        for i, tc in enumerate(tool_calls):
            name = tc.get("function", {}).get("name", "unknown")
            args_len = len(tc.get("function", {}).get("arguments", ""))
            debug("streaming", f"  [{i}] {name} (args: {args_len} chars)", indent=1)

        # Record token usage
        rate_limiter.record_usage(estimated_tokens)

        # Create a response object that mimics ChatCompletion
        class StreamedResponse:
            def __init__(self, content, tool_calls_list):
                self.choices = [self.StreamedChoice(content, tool_calls_list)]
                self.usage = None

            class StreamedChoice:
                def __init__(self, content, tool_calls_list):
                    self.message = self.StreamedMessage(content, tool_calls_list)
                    self.finish_reason = "tool_calls" if tool_calls_list else "stop"

                class StreamedMessage:
                    def __init__(self, content, tool_calls_list):
                        self.content = content
                        self.role = "assistant"
                        self.tool_calls = tool_calls_list if tool_calls_list else None

        return StreamedResponse(full_content, tool_calls if tool_calls else None)

    def switch_model(self, model: str):
        """Switch to a different model.

        Args:
            model: Model identifier
        """
        self.model = model

    def get_available_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get list of available models from API.

        Args:
            force_refresh: Force refresh the model list from API

        Returns:
            List of model dictionaries with id and other metadata
        """
        if self._available_models is None or force_refresh:
            try:
                response = self.client.models.list()
                self._available_models = [
                    {
                        "id": model.id,
                        "object": model.object,
                        "created": model.created,
                        "owned_by": model.owned_by,
                    }
                    for model in response.data
                ]
            except Exception as e:
                print(f"Warning: Could not fetch models: {e}")
                self._available_models = []

        return self._available_models

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limiting status."""
        rate_limiter = get_rate_limiter()
        return rate_limiter.get_current_usage()
