"""Groq API client wrapper with function calling support."""

import os
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Union

from groq import Groq
from groq.types.chat import ChatCompletion, ChatCompletionChunk

from .rate_limiter import get_rate_limiter


class GroqClient:
    """Wrapper for Groq API with enhanced functionality."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        """Initialize Groq client.

        Args:
            api_key: Groq API key
            model: Default model to use
        """
        # Validate API key
        if not api_key or not api_key.strip() or not api_key.startswith("gsk_"):
            print(
                f"⚠️ Warning: API key '{api_key}' appears to be invalid. Groq API keys typically start with 'gsk_'."
            )

        self.client = Groq(api_key=api_key)
        self.model = model
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
    ) -> Union[ChatCompletion, Iterator[ChatCompletionChunk]]:
        """Send a message to the Groq API.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions (function calling)
            tool_choice: Tool choice mode ("auto", "none", or specific tool)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            stream: Whether to stream the response
            callback: Optional callback function for streamed chunks

        Returns:
            ChatCompletion response or stream of ChatCompletionChunk objects

        Raises:
            Exception: If there's an error communicating with the API
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            "timeout": 60,  # Timeout de 60 segundos (consistente con OpenRouter)
        }

        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        # Streaming with tools is now fully supported
        # (Previously disabled to ensure reliable function calling)

        # Smart rate limiting with natural delays
        rate_limiter = get_rate_limiter()
        estimated_tokens = rate_limiter.estimate_tokens(messages, tools)

        # Use smart delay that shows thinking behavior instead of technical messages
        try:
            delayed = rate_limiter.smart_delay(estimated_tokens)
            if delayed:
                print("🔄 Continuing after processing...")
        except KeyboardInterrupt:
            print("\n⏹️  Request cancelled by user")
            return self._create_cancelled_response()

        try:
            # Debug output (respects /debug command)
            import sys
            try:
                from .debug import DEBUG_ENABLED
            except:
                DEBUG_ENABLED = False

            if DEBUG_ENABLED:
                print(f"[DEBUG GroqClient] stream={stream}, has_tools={bool(tools)}", file=sys.stderr, flush=True)

            response = self.client.chat.completions.create(**kwargs)

            if DEBUG_ENABLED:
                print(f"[DEBUG GroqClient] Response type: {type(response)}", file=sys.stderr, flush=True)

            # Record token usage (approximate based on response)
            if hasattr(response, 'usage') and response.usage:
                tokens_used = getattr(response.usage, 'total_tokens', estimated_tokens)
            else:
                tokens_used = estimated_tokens

            rate_limiter.record_usage(tokens_used)

            # Handle streaming - MUST reconstruct response for parsing
            if stream:
                if DEBUG_ENABLED:
                    print(f"[DEBUG GroqClient] Processing stream, reconstructing response", file=sys.stderr, flush=True)

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

                        # Accumulate tool calls (need to merge chunks by index)
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            for tc in delta.tool_calls:
                                tc_index = getattr(tc, 'index', 0)
                                # Extend list if needed
                                while len(accumulated_tool_calls) <= tc_index:
                                    accumulated_tool_calls.append({
                                        'id': '',
                                        'type': 'function',
                                        'function': {'name': '', 'arguments': ''}
                                    })
                                # Merge data
                                if hasattr(tc, 'id') and tc.id:
                                    accumulated_tool_calls[tc_index]['id'] = tc.id
                                if hasattr(tc, 'type') and tc.type:
                                    accumulated_tool_calls[tc_index]['type'] = tc.type
                                if hasattr(tc, 'function') and tc.function:
                                    if hasattr(tc.function, 'name') and tc.function.name:
                                        accumulated_tool_calls[tc_index]['function']['name'] = tc.function.name
                                    if hasattr(tc.function, 'arguments') and tc.function.arguments:
                                        accumulated_tool_calls[tc_index]['function']['arguments'] += tc.function.arguments

                        # Get finish reason
                        if hasattr(chunk.choices[0], 'finish_reason') and chunk.choices[0].finish_reason:
                            finish_reason = chunk.choices[0].finish_reason

                if DEBUG_ENABLED:
                    print(f"[DEBUG GroqClient] Accumulated: content={len(full_content)} chars, tool_calls={len(accumulated_tool_calls)}", file=sys.stderr, flush=True)
                    for i, tc in enumerate(accumulated_tool_calls):
                        print(f"[DEBUG GroqClient]   Tool {i}: {tc['function']['name']} args={tc['function']['arguments'][:50]}...", file=sys.stderr, flush=True)

                # Convert accumulated dicts to proper types
                from groq.types.chat import ChatCompletion, ChatCompletionMessage
                from groq.types.chat.chat_completion import Choice
                from groq.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function

                # Convert tool calls to proper type
                proper_tool_calls = None
                if accumulated_tool_calls:
                    proper_tool_calls = []
                    for tc in accumulated_tool_calls:
                        if tc['function']['name']:  # Only include if we have a name
                            proper_tool_calls.append(ChatCompletionMessageToolCall(
                                id=tc['id'],
                                type=tc['type'],
                                function=Function(
                                    name=tc['function']['name'],
                                    arguments=tc['function']['arguments']
                                )
                            ))

                reconstructed_message = ChatCompletionMessage(
                    role="assistant",
                    content=full_content if full_content else None,
                    tool_calls=proper_tool_calls if proper_tool_calls else None,
                )

                reconstructed_choice = Choice(
                    finish_reason=finish_reason,
                    index=0,
                    message=reconstructed_message,
                )

                response = ChatCompletion(
                    id=f"chatcmpl-{self.model}",
                    choices=[reconstructed_choice],
                    created=0,
                    model=self.model,
                    object="chat.completion",
                )

                if DEBUG_ENABLED:
                    print(f"[DEBUG GroqClient] Reconstructed response type: {type(response)}", file=sys.stderr, flush=True)

            # Validate response has expected structure
            if not stream:
                if not hasattr(response, "choices") or not response.choices:
                    raise ValueError(
                        f"Invalid response from API: missing 'choices'. Got: {response}"
                    )

                # Check that the message has content
                message = response.choices[0].message
                if not hasattr(message, "content") and not hasattr(
                    message, "tool_calls"
                ):
                    raise ValueError(
                        "Response message has neither content nor tool calls"
                    )

            return response

        except Exception as e:
            error_str = str(e).lower()

            # Don't print error for errors we handle gracefully
            if "tool_use_failed" not in error_str and "rate_limit" not in error_str and "429" not in error_str:
                print(f"Error in API communication: {e}")

            # Check if it's an authentication error
            if "auth" in error_str or "key" in error_str or "401" in str(e):
                print(
                    "\n⚠️ AUTHENTICATION ERROR: Your Groq API key may be invalid or expired."
                )
                print(
                    "Current API key:",
                    api_key[:8] + "*" * (len(api_key) - 12) + api_key[-4:]
                    if len(api_key) > 12
                    else "[EMPTY OR INVALID]",
                )
                print("\nPlease check your API key at https://console.groq.com/keys\n")

            # Re-raise - let the caller handle it
            raise

    def _create_cancelled_response(self):
        """Create a response for when rate limit wait is cancelled."""
        class CancelledResponse:
            def __init__(self):
                self.choices = [self.CancelledChoice()]

            class CancelledChoice:
                def __init__(self):
                    self.message = self.CancelledMessage()

                class CancelledMessage:
                    def __init__(self):
                        self.content = "Request cancelled by user during rate limit wait."
                        self.tool_calls = None

        return CancelledResponse()

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limiting status."""
        rate_limiter = get_rate_limiter()
        return rate_limiter.get_current_usage()

    def stream_response(
        self,
        messages: List[Dict[str, Any]],
        callback: Callable[[str], None],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> Generator[str, None, str]:
        """Stream a response from the Groq API with a simpler interface.

        Args:
            messages: List of message dictionaries
            callback: Callback function for each text chunk
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Generator that yields text chunks and finally the complete text
        """
        # Create the chat completion with streaming enabled
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            timeout=30,  # Timeout también para streaming
        )

        # Process the stream
        full_text = ""
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    text_chunk = delta.content
                    full_text += text_chunk
                    callback(text_chunk)
                    yield text_chunk

        return full_text

    def switch_model(self, model: str):
        """Switch to a different model.

        Args:
            model: Model identifier
        """
        self.model = model

    def get_available_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get list of available models from Groq API.

        Args:
            force_refresh: Force refresh the model list from API

        Returns:
            List of model dictionaries with id and other metadata
        """
        if self._available_models is None or force_refresh:
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

        return self._available_models

    def categorize_models(self) -> Dict[str, List[str]]:
        """Categorize available models by type.

        Returns:
            Dictionary with categories as keys and model IDs as values
        """
        models = self.get_available_models()
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

    def test_function_calling(self, model: Optional[str] = None) -> bool:
        """Test if a model supports function calling.

        Args:
            model: Model to test (defaults to current model)

        Returns:
            True if model supports function calling, False otherwise
        """
        test_model = model or self.model

        test_tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_function",
                    "description": "A test function",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "test": {"type": "string", "description": "Test parameter"}
                        },
                        "required": ["test"],
                    },
                },
            }
        ]

        try:
            # Save current model
            original_model = self.model
            self.model = test_model

            # Try to call with tools
            self.send_message(
                messages=[{"role": "user", "content": "Test"}],
                tools=test_tools,
                max_tokens=10,
            )

            # Restore original model
            self.model = original_model
            return True

        except Exception as e:
            # Restore original model
            self.model = original_model

            error_msg = str(e).lower()
            if "does not support" in error_msg or "not supported" in error_msg:
                return False
            # For other errors, assume it might support it
            return True
