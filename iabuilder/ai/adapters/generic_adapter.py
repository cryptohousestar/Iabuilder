"""Generic fallback adapter for unknown model families.

This adapter is used when a model doesn't match any known family.
It provides basic functionality with multiple fallback parsing strategies.
"""

import json
import re
from typing import Any, Dict, List, Optional

from .base import AbstractAdapter, ToolCall


class GenericAdapter(AbstractAdapter):
    """Generic adapter for unknown model families.

    This adapter:
    - Uses standard OpenAI-compatible parsing
    - Includes multiple fallback strategies for malformed tool calls
    - Works as a safe default for untested models
    """

    family_name = "generic"
    support_level = "experimental"
    model_patterns = []  # Matches nothing - used as fallback

    supports_tools = True
    supports_parallel_tools = True
    supports_streaming = True
    supports_native_tool_messages = False  # Use text format for unknown models (safer)

    # All known malformed patterns for fallback parsing
    MALFORMED_PATTERNS = [
        # Standard XML with space
        re.compile(r'<function=(\w+)\s+(\{[^>]+\})(?:>?\s*</function>|/>)', re.DOTALL | re.IGNORECASE),
        # No space before JSON
        re.compile(r'<function=(\w+)(\{[^>]+\})(?:>?\s*</function>|/>)', re.DOTALL | re.IGNORECASE),
        # Array syntax
        re.compile(r'<function=(\w+)\s*\[(\{[^>]+\})\](?:>?\s*</function>|/>)', re.DOTALL | re.IGNORECASE),
        # Empty brackets
        re.compile(r'<function=(\w+)\[\](\{[^>]+\})(?:>?\s*</function>|/>)', re.DOTALL | re.IGNORECASE),
        # Parentheses wrapper
        re.compile(r'<function=(\w+)\((\{[^)]+\})\)(?:>?\s*</function>|/>)', re.DOTALL | re.IGNORECASE),
    ]

    # Tool code patterns (from Gemini-style models)
    TOOL_CODE_PATTERN = re.compile(r'```tool_code\s*\n(.*?)```', re.DOTALL | re.IGNORECASE)
    TOOL_CODE_CALL_PATTERN = re.compile(
        r'(?:print\s*\(\s*)?default_api\.(\w+)\s*\(\s*(.*?)\s*\)\s*\)?',
        re.DOTALL
    )

    # Combined cleaning pattern
    CLEAN_PATTERN = re.compile(
        r'<function=\w+[\s\[\]\(]*\{[^>)]+\}[\s\]\)]*(?:>?\s*</function>|/>)',
        re.DOTALL | re.IGNORECASE
    )

    def get_system_prompt_additions(self) -> str:
        """Add basic guidance for tool use."""
        return """When using tools, please use the function calling interface provided.
Format your tool calls with proper JSON arguments."""

    def parse_native_tool_calls(self, response: Any) -> List[ToolCall]:
        """Parse tool calls using OpenAI-compatible format."""
        tool_calls = []

        try:
            if not hasattr(response, 'choices') or not response.choices:
                return []

            message = response.choices[0].message

            if not hasattr(message, 'tool_calls') or not message.tool_calls:
                return []

            for tc in message.tool_calls:
                tool_call = self._parse_single_tool_call(tc)
                if tool_call:
                    tool_calls.append(tool_call)

        except Exception:
            pass

        return tool_calls

    def _parse_single_tool_call(self, tc: Any) -> Optional[ToolCall]:
        """Parse a single tool call from various formats."""
        try:
            if isinstance(tc, dict):
                # OpenAI format
                if "function" in tc:
                    func = tc["function"]
                    tc_id = tc.get("id", "unknown")
                    name = func.get("name", "unknown")
                    args = func.get("arguments", {})
                # Alternative format
                else:
                    tc_id = tc.get("id", tc.get("call_id", "unknown"))
                    name = tc.get("name", "unknown")
                    args = tc.get("args", tc.get("arguments", {}))

                if isinstance(args, str):
                    args = json.loads(args) if args else {}

                return ToolCall(id=tc_id, name=name, arguments=args)

            else:
                tc_id = getattr(tc, 'id', getattr(tc, 'call_id', 'unknown'))
                func = getattr(tc, 'function', None)

                if func:
                    name = getattr(func, 'name', 'unknown')
                    args = getattr(func, 'arguments', '{}')
                else:
                    name = getattr(tc, 'name', 'unknown')
                    args = getattr(tc, 'args', getattr(tc, 'arguments', {}))

                if isinstance(args, str):
                    args = json.loads(args) if args else {}

                return ToolCall(id=tc_id, name=name, arguments=args)

        except Exception:
            return None

    def parse_fallback_tool_calls(self, content: str) -> List[ToolCall]:
        """Parse tool calls from text using multiple strategies."""
        if not content:
            return []

        tool_calls = []
        call_index = 0
        seen = set()

        # Strategy 1: XML-style function calls
        for pattern in self.MALFORMED_PATTERNS:
            for match in pattern.finditer(content):
                name = match.group(1)
                args_str = match.group(2)

                key = f"{name}:{args_str}"
                if key in seen:
                    continue
                seen.add(key)

                arguments = self._try_parse_json(args_str)
                if arguments is not None:
                    tool_calls.append(ToolCall(
                        id=f"fallback_{call_index}",
                        name=name,
                        arguments=arguments,
                    ))
                    call_index += 1

        # Strategy 2: tool_code blocks
        for match in self.TOOL_CODE_PATTERN.finditer(content):
            block = match.group(1)

            for call_match in self.TOOL_CODE_CALL_PATTERN.finditer(block):
                name = call_match.group(1)
                params_str = call_match.group(2)

                key = f"{name}:{params_str}"
                if key in seen:
                    continue
                seen.add(key)

                arguments = self._parse_python_params(params_str)
                if arguments is not None:
                    tool_calls.append(ToolCall(
                        id=f"toolcode_{call_index}",
                        name=name,
                        arguments=arguments,
                    ))
                    call_index += 1

        return tool_calls

    def _try_parse_json(self, json_str: str) -> Optional[Dict]:
        """Try to parse JSON with various fixes."""
        if not json_str:
            return None

        # Try as-is
        try:
            return json.loads(json_str)
        except:
            pass

        # Try replacing quotes
        try:
            fixed = json_str.replace("'", '"')
            return json.loads(fixed)
        except:
            pass

        # Try adding quotes to keys
        try:
            fixed = re.sub(r'(\w+):', r'"\1":', json_str)
            return json.loads(fixed)
        except:
            pass

        return None

    def _parse_python_params(self, params_str: str) -> Optional[Dict]:
        """Parse Python-style parameters."""
        if not params_str.strip():
            return {}

        result = {}
        pattern = re.compile(
            r'(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\d+|True|False|None)',
            re.DOTALL
        )

        for match in pattern.finditer(params_str):
            name = match.group(1)
            value = match.group(2)

            try:
                if value.startswith('"') or value.startswith("'"):
                    result[name] = value[1:-1]
                elif value == 'True':
                    result[name] = True
                elif value == 'False':
                    result[name] = False
                elif value == 'None':
                    result[name] = None
                elif value.isdigit():
                    result[name] = int(value)
                else:
                    result[name] = value
            except:
                result[name] = value

        return result if result else None

    def clean_content(self, content: str) -> str:
        """Remove all known tool call patterns from content."""
        # Remove XML-style
        cleaned = self.CLEAN_PATTERN.sub('', content)

        # Remove tool_code blocks
        cleaned = self.TOOL_CODE_PATTERN.sub('', cleaned)

        return cleaned.strip()

    def get_support_level_for_model(self, model_name: str) -> str:
        """All generic models are experimental."""
        return "experimental"
