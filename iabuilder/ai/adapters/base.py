"""Abstract base class for model family adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """Normalized tool call representation.

    All adapters convert their model-specific format to this standard format.
    """
    id: str
    name: str
    arguments: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }

    def to_api_format(self) -> Dict[str, Any]:
        """Convert to OpenAI/OpenRouter API format for conversation history.

        This format is required when including tool_calls in assistant messages.
        """
        import json
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments) if isinstance(self.arguments, dict) else str(self.arguments)
            }
        }


@dataclass
class ParsedResponse:
    """Normalized parsed response from any model.

    Contains extracted content, tool calls, and metadata.
    """
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    raw_response: Any = None

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0


class AbstractAdapter(ABC):
    """Abstract base class for model family adapters.

    Each adapter handles the specific behaviors of a model family:
    - How to format the system prompt
    - How to format tool definitions
    - How to parse tool calls from responses
    - How to handle fallback parsing for malformed responses
    """

    # Override in subclasses
    family_name: str = "unknown"
    support_level: str = "experimental"  # "optimized", "compatible", "experimental"

    # Model detection patterns (override in subclasses)
    model_patterns: List[str] = []

    # Capabilities (override in subclasses)
    supports_tools: bool = True
    supports_parallel_tools: bool = True
    supports_streaming: bool = True
    supports_native_tool_messages: bool = False  # If True, use role:tool format instead of converting to text

    def __init__(self, model_name: str):
        """Initialize adapter for a specific model.

        Args:
            model_name: The model identifier (e.g., "gpt-4o", "gemini-2.0-flash")
        """
        self.model_name = model_name
        self._update_capabilities_for_model()

    def _update_capabilities_for_model(self):
        """Update capabilities based on specific model. Override if needed."""
        pass

    # =========================================================================
    # REQUEST PREPARATION METHODS
    # =========================================================================

    def prepare_request(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prepare a complete request for the model.

        Args:
            messages: Conversation messages
            tools: Tool definitions
            system_prompt: Optional additional system prompt

        Returns:
            Dictionary with prepared messages and tools
        """
        prepared_messages = self.format_messages(messages, system_prompt)
        prepared_tools = self.format_tools(tools) if tools else None

        return {
            "messages": prepared_messages,
            "tools": prepared_tools,
        }

    def format_messages(
        self,
        messages: List[Dict[str, Any]],
        additional_system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Format messages for this model family.

        Default implementation adds family-specific instructions to system prompt.
        Override for custom message formatting.

        Args:
            messages: Original messages
            additional_system_prompt: Optional additional instructions

        Returns:
            Formatted messages
        """
        formatted = []
        system_additions = self.get_system_prompt_additions()

        for msg in messages:
            if msg.get("role") == "system":
                # Enhance system message with family-specific instructions
                content = msg.get("content", "")
                if system_additions:
                    content = f"{content}\n\n{system_additions}"
                if additional_system_prompt:
                    content = f"{content}\n\n{additional_system_prompt}"
                formatted.append({**msg, "content": content})
            else:
                formatted.append(msg.copy())

        return formatted

    def get_system_prompt_additions(self) -> str:
        """Get family-specific system prompt additions.

        Override in subclasses to add instructions specific to the model family.

        Returns:
            Additional system prompt text
        """
        return ""

    def format_tools(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format tool definitions for this model family.

        Default implementation returns tools as-is (OpenAI format).
        Override for models that need different tool formats.

        Args:
            tools: Tool definitions in OpenAI format

        Returns:
            Formatted tool definitions
        """
        return tools

    # =========================================================================
    # RESPONSE PARSING METHODS
    # =========================================================================

    def parse_response(self, response: Any) -> ParsedResponse:
        """Parse a model response into normalized format.

        This is the main entry point for response parsing. It:
        1. Tries to extract native tool calls
        2. Extracts text content
        3. If no native tool calls, tries fallback parsing

        Args:
            response: Raw response from the model API

        Returns:
            ParsedResponse with normalized content and tool calls
        """
        # Extract content
        content = self.extract_content(response)

        # Try native tool calls first
        tool_calls = self.parse_native_tool_calls(response)

        # If no native tool calls, try fallback parsing from content
        if not tool_calls and content:
            tool_calls = self.parse_fallback_tool_calls(content)

            # Clean content if we found fallback tool calls
            if tool_calls:
                content = self.clean_content(content)

        # Get finish reason
        finish_reason = self.extract_finish_reason(response)

        return ParsedResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            raw_response=response,
        )

    @abstractmethod
    def parse_native_tool_calls(self, response: Any) -> List[ToolCall]:
        """Parse native tool calls from the model response.

        This should extract tool calls in the model's native format
        and convert them to normalized ToolCall objects.

        Args:
            response: Raw model response

        Returns:
            List of normalized ToolCall objects
        """
        pass

    def parse_fallback_tool_calls(self, content: str) -> List[ToolCall]:
        """Parse tool calls from response text when native parsing fails.

        This is used when models output tool calls in text format instead
        of using the native tool calling mechanism.

        Default implementation returns empty list.
        Override in subclasses that need fallback parsing.

        Args:
            content: Response text content

        Returns:
            List of ToolCall objects parsed from text
        """
        return []

    def extract_content(self, response: Any) -> str:
        """Extract text content from response.

        Args:
            response: Raw model response

        Returns:
            Text content
        """
        try:
            if hasattr(response, 'choices') and response.choices:
                message = response.choices[0].message
                if hasattr(message, 'content') and message.content:
                    return message.content.strip()
            return ""
        except Exception:
            return ""

    def extract_finish_reason(self, response: Any) -> str:
        """Extract finish reason from response.

        Args:
            response: Raw model response

        Returns:
            Finish reason string
        """
        try:
            if hasattr(response, 'choices') and response.choices:
                return getattr(response.choices[0], 'finish_reason', 'stop') or 'stop'
            return "stop"
        except Exception:
            return "stop"

    def clean_content(self, content: str) -> str:
        """Clean content by removing parsed tool call artifacts.

        Override in subclasses to remove family-specific tool call patterns.

        Args:
            content: Original content

        Returns:
            Cleaned content
        """
        return content

    # =========================================================================
    # MODEL INFO METHODS
    # =========================================================================

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about this adapter and model.

        Returns:
            Dictionary with model/adapter information
        """
        return {
            "model": self.model_name,
            "family": self.family_name,
            "support_level": self.support_level,
            "supports_tools": self.supports_tools,
            "supports_parallel_tools": self.supports_parallel_tools,
            "supports_streaming": self.supports_streaming,
        }

    def get_support_level_for_model(self, model_name: str) -> str:
        """Get support level for a specific model.

        Override to provide model-specific support levels.

        Args:
            model_name: Model identifier

        Returns:
            Support level: "optimized", "compatible", or "experimental"
        """
        return self.support_level

    @classmethod
    def matches_model(cls, model_name: str) -> bool:
        """Check if this adapter handles the given model.

        Args:
            model_name: Model identifier

        Returns:
            True if this adapter should handle this model
        """
        model_lower = model_name.lower()
        return any(pattern in model_lower for pattern in cls.model_patterns)
