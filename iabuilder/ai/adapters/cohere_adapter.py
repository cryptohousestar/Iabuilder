"""Cohere family adapter.

Handles: Command R, Command R+, Command
"""

import json
import re
from typing import Any, Dict, List, Optional

from .base import AbstractAdapter, ToolCall


class CohereAdapter(AbstractAdapter):
    """Adapter for Cohere Command models.

    Cohere Command R and R+ have good function calling support via OpenRouter.
    """

    family_name = "cohere"
    support_level = "compatible"
    model_patterns = ["command", "cohere", "command-r", "command-r-plus"]

    supports_tools = True
    supports_parallel_tools = True
    supports_streaming = True
    supports_native_tool_messages = True  # Cohere via OpenRouter supports native tool format

    def _update_capabilities_for_model(self):
        """Update capabilities based on model."""
        model_lower = self.model_name.lower()

        # Command R+ is most capable
        if "command-r-plus" in model_lower or "command-r+" in model_lower:
            self.support_level = "compatible"

        # Command R is good
        if "command-r" in model_lower:
            self.support_level = "compatible"

    def get_system_prompt_additions(self) -> str:
        """No special additions needed for Cohere."""
        return ""

    def parse_native_tool_calls(self, response: Any) -> List[ToolCall]:
        """Parse Cohere tool calls (OpenAI-compatible format via OpenRouter)."""
        tool_calls = []

        try:
            if not hasattr(response, 'choices') or not response.choices:
                return []

            message = response.choices[0].message

            if not hasattr(message, 'tool_calls') or not message.tool_calls:
                return []

            for tc in message.tool_calls:
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

    def parse_fallback_tool_calls(self, content: str) -> List[ToolCall]:
        """Parse XML-style function calls that Cohere might output."""
        if not content:
            return []

        tool_calls = []
        call_index = 0

        pattern = re.compile(
            r'<function=(\w+)\s*(\{[^>]+\})(?:>?\s*</function>|/>)',
            re.DOTALL
        )

        seen = set()
        for match in pattern.finditer(content):
            name = match.group(1)
            args_str = match.group(2)

            key = f"{name}:{args_str}"
            if key in seen:
                continue
            seen.add(key)

            try:
                arguments = json.loads(args_str)
                tool_calls.append(ToolCall(
                    id=f"fallback_{call_index}",
                    name=name,
                    arguments=arguments,
                ))
                call_index += 1
            except json.JSONDecodeError:
                pass

        return tool_calls

    def clean_content(self, content: str) -> str:
        """Remove XML-style tool calls from content."""
        pattern = re.compile(
            r'<function=\w+\s*\{[^>]+\}(?:>?\s*</function>|/>)',
            re.DOTALL
        )
        return pattern.sub('', content).strip()

    def get_support_level_for_model(self, model_name: str) -> str:
        """Get support level for specific Cohere model."""
        model_lower = model_name.lower()

        # Command R+
        if "command-r-plus" in model_lower or "command-r+" in model_lower:
            return "compatible"

        # Command R
        if "command-r" in model_lower:
            return "compatible"

        # Command (older)
        if "command" in model_lower:
            return "compatible"

        return "compatible"
