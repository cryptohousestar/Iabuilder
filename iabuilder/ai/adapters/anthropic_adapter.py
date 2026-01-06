"""Anthropic/Claude family adapter.

Handles: Claude 3.x, Claude 3.5, Claude 4.x (future)
"""

import json
import re
from typing import Any, Dict, List, Optional

from .base import AbstractAdapter, ToolCall, ParsedResponse


class AnthropicAdapter(AbstractAdapter):
    """Adapter for Anthropic Claude models.

    Claude uses a specific format for tool use with tool_use blocks.
    When accessed through OpenRouter, responses are normalized to OpenAI format.
    """

    family_name = "anthropic"
    support_level = "optimized"
    model_patterns = ["claude", "anthropic/claude"]

    supports_tools = True
    supports_parallel_tools = True
    supports_streaming = True
    supports_native_tool_messages = True  # Claude supports native tool format via OpenRouter

    def _update_capabilities_for_model(self):
        """Update capabilities based on specific model."""
        model_lower = self.model_name.lower()

        # Claude 3.5 Sonnet is the most capable
        if "claude-3.5-sonnet" in model_lower or "claude-3-5-sonnet" in model_lower:
            self.support_level = "optimized"

        # Claude 3 Opus is excellent
        elif "claude-3-opus" in model_lower:
            self.support_level = "optimized"

        # Claude 3 Haiku is fast but capable
        elif "claude-3-haiku" in model_lower:
            self.support_level = "optimized"

    def get_system_prompt_additions(self) -> str:
        """No additions needed - Claude has excellent tool support."""
        return ""

    def parse_native_tool_calls(self, response: Any) -> List[ToolCall]:
        """Parse Claude tool calls.

        When using Claude through OpenRouter, the format is normalized
        to OpenAI format. Direct Anthropic API uses tool_use blocks.

        This handles both formats.
        """
        tool_calls = []

        try:
            if not hasattr(response, 'choices') or not response.choices:
                # Try Anthropic native format
                return self._parse_anthropic_native(response)

            message = response.choices[0].message

            # OpenAI-compatible format (from OpenRouter)
            if hasattr(message, 'tool_calls') and message.tool_calls:
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

    def _parse_anthropic_native(self, response: Any) -> List[ToolCall]:
        """Parse native Anthropic API format.

        Anthropic format:
        response.content = [
            {"type": "text", "text": "..."},
            {"type": "tool_use", "id": "xxx", "name": "tool", "input": {...}}
        ]
        """
        tool_calls = []

        try:
            content = getattr(response, 'content', [])
            if not isinstance(content, list):
                return []

            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_calls.append(ToolCall(
                        id=block.get("id", "unknown"),
                        name=block.get("name", "unknown"),
                        arguments=block.get("input", {}),
                    ))
                elif hasattr(block, 'type') and block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        id=getattr(block, 'id', 'unknown'),
                        name=getattr(block, 'name', 'unknown'),
                        arguments=getattr(block, 'input', {}),
                    ))

        except Exception:
            pass

        return tool_calls

    def parse_fallback_tool_calls(self, content: str) -> List[ToolCall]:
        """Parse malformed XML-style tool calls that Claude sometimes outputs.

        Claude occasionally outputs tool calls in XML format when confused:
        <function=tool_name {"param": "value"}></function>
        """
        if not content:
            return []

        tool_calls = []
        call_index = 0

        # Pattern for XML-style function calls
        patterns = [
            re.compile(r'<function=(\w+)\s+(\{[^>]+\})(?:>?\s*</function>|/>)', re.DOTALL),
            re.compile(r'<function=(\w+)(\{[^>]+\})(?:>?\s*</function>|/>)', re.DOTALL),
        ]

        seen = set()
        for pattern in patterns:
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
            r'<function=\w+[\s\[\]\(]*\{[^>)]+\}[\s\]\)]*(?:>?\s*</function>|/>)',
            re.DOTALL
        )
        return pattern.sub('', content).strip()

    def get_support_level_for_model(self, model_name: str) -> str:
        """Get support level for specific Claude model."""
        model_lower = model_name.lower()

        # Claude 3.5 Sonnet is top tier
        if "claude-3.5-sonnet" in model_lower or "claude-3-5-sonnet" in model_lower:
            return "optimized"

        # Claude 3 Opus
        if "claude-3-opus" in model_lower:
            return "optimized"

        # Claude 3 Sonnet
        if "claude-3-sonnet" in model_lower:
            return "optimized"

        # Claude 3 Haiku
        if "claude-3-haiku" in model_lower:
            return "optimized"

        # Older Claude versions
        if "claude-2" in model_lower:
            return "compatible"

        return "compatible"
