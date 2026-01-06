"""Meta/Llama family adapter.

Handles: Llama 2, Llama 3, Llama 3.1, Llama 3.3, Llama 4 (future)
"""

import json
import re
from typing import Any, Dict, List, Optional

from .base import AbstractAdapter, ToolCall, ParsedResponse


class MetaAdapter(AbstractAdapter):
    """Adapter for Meta Llama models.

    Llama models have good function calling support, especially 70B+ variants.
    Smaller models (8B) may be less reliable with complex tool calls.
    """

    family_name = "meta"
    support_level = "compatible"
    model_patterns = ["llama", "meta-llama", "meta/llama"]

    supports_tools = True
    supports_parallel_tools = True
    supports_streaming = True
    supports_native_tool_messages = True  # Llama via OpenRouter supports native tool format

    def _update_capabilities_for_model(self):
        """Update capabilities based on model size."""
        model_lower = self.model_name.lower()

        # 70B models are most reliable
        if "70b" in model_lower:
            self.support_level = "optimized"
        # 8B models are less reliable with complex tools
        elif "8b" in model_lower:
            self.support_level = "compatible"
        # 405B is excellent
        elif "405b" in model_lower:
            self.support_level = "optimized"

    def get_system_prompt_additions(self) -> str:
        """Add instructions for consistent tool use."""
        model_lower = self.model_name.lower()

        # Smaller models need more guidance
        if "8b" in model_lower:
            return """When using tools, always use the function calling interface provided.
Format your tool calls correctly with proper JSON arguments."""

        return ""

    def parse_native_tool_calls(self, response: Any) -> List[ToolCall]:
        """Parse Llama tool calls.

        Llama through providers like Groq/OpenRouter uses OpenAI-compatible format.
        """
        tool_calls = []

        # Import debug flag
        import sys
        try:
            from ...debug import DEBUG_ENABLED
        except:
            DEBUG_ENABLED = True  # Fallback

        try:
            if DEBUG_ENABLED:
                print(f"[DEBUG MetaAdapter] Parsing response type: {type(response)}", file=sys.stderr, flush=True)

            if not hasattr(response, 'choices') or not response.choices:
                if DEBUG_ENABLED:
                    print(f"[DEBUG MetaAdapter] No choices in response", file=sys.stderr, flush=True)
                return []

            message = response.choices[0].message
            if DEBUG_ENABLED:
                print(f"[DEBUG MetaAdapter] Message type: {type(message)}", file=sys.stderr, flush=True)
                content_preview = getattr(message, 'content', None) or 'NO CONTENT'
                print(f"[DEBUG MetaAdapter] Message content: {content_preview[:100]}", file=sys.stderr, flush=True)
                print(f"[DEBUG MetaAdapter] Has tool_calls attr: {hasattr(message, 'tool_calls')}", file=sys.stderr, flush=True)
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    print(f"[DEBUG MetaAdapter] tool_calls count: {len(message.tool_calls)}", file=sys.stderr, flush=True)
                    for i, tc in enumerate(message.tool_calls):
                        print(f"[DEBUG MetaAdapter]   tc[{i}] type={type(tc)}, id={getattr(tc, 'id', '?')}", file=sys.stderr, flush=True)

            if not hasattr(message, 'tool_calls') or not message.tool_calls:
                if DEBUG_ENABLED:
                    print(f"[DEBUG MetaAdapter] No tool_calls in message", file=sys.stderr, flush=True)
                return []

            if DEBUG_ENABLED:
                print(f"[DEBUG MetaAdapter] Found {len(message.tool_calls)} tool calls", file=sys.stderr, flush=True)

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

                if DEBUG_ENABLED:
                    print(f"[DEBUG MetaAdapter] Tool call: {name} with args: {args_str[:100]}", file=sys.stderr, flush=True)

                try:
                    if isinstance(args_str, dict):
                        arguments = args_str
                    else:
                        arguments = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError as e:
                    if DEBUG_ENABLED:
                        print(f"[DEBUG MetaAdapter] JSON decode error: {e}", file=sys.stderr, flush=True)
                    arguments = {}

                tool_calls.append(ToolCall(
                    id=tc_id,
                    name=name,
                    arguments=arguments,
                ))

        except Exception as e:
            if DEBUG_ENABLED:
                print(f"[DEBUG MetaAdapter] Exception in parse_native_tool_calls: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                import traceback
                traceback.print_exc()

        if DEBUG_ENABLED:
            print(f"[DEBUG MetaAdapter] Returning {len(tool_calls)} tool calls", file=sys.stderr, flush=True)
        return tool_calls

    def parse_fallback_tool_calls(self, content: str) -> List[ToolCall]:
        """Parse XML-style function calls that Llama sometimes outputs.

        Llama models occasionally output malformed tool calls like:
        <function=tool_name {"param": "value"}></function>
        """
        if not content:
            return []

        tool_calls = []
        call_index = 0

        patterns = [
            # Standard XML format with space
            re.compile(r'<function=(\w+)\s+(\{[^>]+\})(?:>?\s*</function>|/>)', re.DOTALL),
            # No space before JSON
            re.compile(r'<function=(\w+)(\{[^>]+\})(?:>?\s*</function>|/>)', re.DOTALL),
            # Array syntax
            re.compile(r'<function=(\w+)\s*\[(\{[^>]+\})\](?:>?\s*</function>|/>)', re.DOTALL),
            # Empty brackets
            re.compile(r'<function=(\w+)\[\](\{[^>]+\})(?:>?\s*</function>|/>)', re.DOTALL),
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
                    # Try fixing common JSON issues
                    fixed = args_str.replace("'", '"')
                    try:
                        arguments = json.loads(fixed)
                        tool_calls.append(ToolCall(
                            id=f"fallback_{call_index}",
                            name=name,
                            arguments=arguments,
                        ))
                        call_index += 1
                    except:
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
        """Get support level for specific Llama model."""
        model_lower = model_name.lower()

        # Llama 3.3 70B is excellent
        if "llama-3.3" in model_lower and "70b" in model_lower:
            return "optimized"

        # Llama 3.1 405B is excellent
        if "405b" in model_lower:
            return "optimized"

        # Llama 3.1 70B is very good
        if "llama-3.1" in model_lower and "70b" in model_lower:
            return "optimized"

        # 70B models in general are good
        if "70b" in model_lower:
            return "compatible"

        # 8B models are less reliable
        if "8b" in model_lower:
            return "compatible"

        # Llama 2 is older
        if "llama-2" in model_lower:
            return "compatible"

        return "compatible"
