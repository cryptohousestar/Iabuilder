"""OpenAI/GPT family adapter.

Handles: GPT-4, GPT-4o, GPT-3.5, o1, o3 series
"""

import json
from typing import Any, Dict, List, Optional

from .base import AbstractAdapter, ToolCall, ParsedResponse


class OpenAIAdapter(AbstractAdapter):
    """Adapter for OpenAI GPT models.

    These models have excellent native function calling support.
    This is the "reference" implementation as OpenAI's format is
    the de facto standard.
    """

    family_name = "openai"
    support_level = "optimized"
    model_patterns = ["gpt-4", "gpt-3.5", "gpt-4o", "o1-", "o3-", "chatgpt"]

    supports_tools = True
    supports_parallel_tools = True
    supports_streaming = True
    supports_native_tool_messages = True  # OpenAI format is the reference standard

    def _update_capabilities_for_model(self):
        """Update capabilities based on specific model."""
        model_lower = self.model_name.lower()

        # o1/o3 reasoning models have limited streaming
        if "o1-" in model_lower or "o3-" in model_lower:
            self.supports_streaming = False
            self.support_level = "compatible"

    def get_system_prompt_additions(self) -> str:
        """No additions needed - GPT models work great with tools."""
        return ""

    def parse_native_tool_calls(self, response: Any) -> List[ToolCall]:
        """Parse OpenAI-format tool calls.

        OpenAI format:
        response.choices[0].message.tool_calls = [
            {
                "id": "call_xxx",
                "type": "function",
                "function": {
                    "name": "tool_name",
                    "arguments": "{\"param\": \"value\"}"
                }
            }
        ]
        """
        tool_calls = []

        try:
            if not hasattr(response, 'choices') or not response.choices:
                return []

            message = response.choices[0].message

            if not hasattr(message, 'tool_calls') or not message.tool_calls:
                return []

            for tc in message.tool_calls:
                # Handle both object and dict formats
                if isinstance(tc, dict):
                    tc_id = tc.get("id", "unknown")
                    func = tc.get("function", {})
                    name = func.get("name", "unknown")
                    args_str = func.get("arguments", "{}")
                else:
                    tc_id = getattr(tc, 'id', 'unknown')
                    func = getattr(tc, 'function', None)
                    if func:
                        name = getattr(func, 'name', 'unknown')
                        args_str = getattr(func, 'arguments', '{}')
                    else:
                        continue

                # Parse arguments
                try:
                    if isinstance(args_str, dict):
                        arguments = args_str
                    else:
                        arguments = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError:
                    arguments = {}

                tool_calls.append(ToolCall(
                    id=tc_id,
                    name=name,
                    arguments=arguments,
                ))

        except Exception:
            pass

        return tool_calls

    def get_support_level_for_model(self, model_name: str) -> str:
        """Get support level for specific OpenAI model."""
        model_lower = model_name.lower()

        # GPT-4o and GPT-4-turbo are fully optimized
        if "gpt-4o" in model_lower or "gpt-4-turbo" in model_lower:
            return "optimized"

        # GPT-4 base is optimized
        if "gpt-4" in model_lower:
            return "optimized"

        # GPT-3.5 is compatible
        if "gpt-3.5" in model_lower:
            return "compatible"

        # o1/o3 reasoning models are compatible
        if "o1-" in model_lower or "o3-" in model_lower:
            return "compatible"

        return "compatible"
