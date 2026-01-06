"""Qwen family adapter.

Handles: Qwen 2, Qwen 2.5, Qwen-VL (vision)
"""

import json
import re
from typing import Any, Dict, List, Optional

from .base import AbstractAdapter, ToolCall


class QwenAdapter(AbstractAdapter):
    """Adapter for Alibaba Qwen models.

    Qwen models have good function calling support, similar to OpenAI format.
    """

    family_name = "qwen"
    support_level = "compatible"
    model_patterns = ["qwen", "qwen2", "alibaba/qwen"]

    supports_tools = True
    supports_parallel_tools = True
    supports_streaming = True
    supports_native_tool_messages = True  # Qwen via OpenRouter supports native tool format

    def _update_capabilities_for_model(self):
        """Update capabilities based on model."""
        model_lower = self.model_name.lower()

        # Qwen 2.5 72B is most capable
        if "qwen-2.5" in model_lower and "72b" in model_lower:
            self.support_level = "compatible"
        elif "qwen2.5" in model_lower and "72b" in model_lower:
            self.support_level = "compatible"

    def get_system_prompt_additions(self) -> str:
        """No special additions needed for Qwen."""
        return ""

    def parse_native_tool_calls(self, response: Any) -> List[ToolCall]:
        """Parse Qwen tool calls (OpenAI-compatible format)."""
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
        """Parse XML-style function calls."""
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
        """Get support level for specific Qwen model."""
        model_lower = model_name.lower()

        # Qwen 2.5 72B
        if ("qwen-2.5" in model_lower or "qwen2.5" in model_lower) and "72b" in model_lower:
            return "compatible"

        # Qwen 2.5 Coder
        if "coder" in model_lower:
            return "compatible"

        return "compatible"
