"""Debug utilities for IABuilder development.

Centralized debug logging that can be enabled/disabled easily.
Set DEBUG_ENABLED = False to disable all debug output.
"""

import json
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime

# Master switch for debug output
DEBUG_ENABLED = True

# Granular debug flags
DEBUG_FLAGS = {
    "chat": True,        # Chat flow: messages sent/received
    "tools": True,       # Tool calls: detection, parsing, execution
    "streaming": True,   # Streaming: chunks, accumulation
    "adapters": True,    # Adapters: which one, what it parses
    "api": True,         # API requests/responses
    "context": True,     # Context/conversation management
}

# Colors for terminal output
COLORS = {
    "reset": "\033[0m",
    "dim": "\033[90m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "bold": "\033[1m",
}

# Category colors
CATEGORY_COLORS = {
    "chat": "cyan",
    "tools": "yellow",
    "streaming": "magenta",
    "adapters": "blue",
    "api": "green",
    "context": "dim",
}


def debug(category: str, message: str, data: Any = None, indent: int = 0):
    """Print debug message if debugging is enabled for category.

    Args:
        category: Debug category (chat, tools, streaming, adapters, api, context)
        message: Debug message
        data: Optional data to display (will be formatted)
        indent: Indentation level
    """
    if not DEBUG_ENABLED:
        return

    if category not in DEBUG_FLAGS or not DEBUG_FLAGS[category]:
        return

    # Get color for category
    color = COLORS.get(CATEGORY_COLORS.get(category, "dim"), COLORS["dim"])
    reset = COLORS["reset"]

    # Build prefix
    prefix = "  " * indent
    tag = f"[{category.upper():^10}]"

    # Print message
    print(f"{color}{prefix}{tag} {message}{reset}", file=sys.stderr)

    # Print data if provided
    if data is not None:
        _print_data(data, color, prefix, indent + 1)


def debug_separator(category: str, title: str = ""):
    """Print a visual separator."""
    if not DEBUG_ENABLED or not DEBUG_FLAGS.get(category, False):
        return

    color = COLORS.get(CATEGORY_COLORS.get(category, "dim"), COLORS["dim"])
    reset = COLORS["reset"]

    if title:
        line = f"{'─' * 20} {title} {'─' * 20}"
    else:
        line = "─" * 50

    print(f"{color}{line}{reset}", file=sys.stderr)


def debug_tool_call(name: str, args: Dict[str, Any], call_id: str = ""):
    """Debug a tool call."""
    if not DEBUG_ENABLED or not DEBUG_FLAGS.get("tools", False):
        return

    color = COLORS["yellow"]
    reset = COLORS["reset"]
    bold = COLORS["bold"]

    print(f"{color}[  TOOLS   ] {bold}Tool Call:{reset} {color}{name}{reset}", file=sys.stderr)
    print(f"{color}            ID: {call_id}{reset}", file=sys.stderr)

    # Show args (truncated if too long)
    args_str = json.dumps(args, ensure_ascii=False, indent=2)
    if len(args_str) > 200:
        args_str = args_str[:200] + "..."
    for line in args_str.split('\n'):
        print(f"{color}            {line}{reset}", file=sys.stderr)


def debug_tool_result(name: str, success: bool, result: Any):
    """Debug a tool result."""
    if not DEBUG_ENABLED or not DEBUG_FLAGS.get("tools", False):
        return

    color = COLORS["green"] if success else COLORS["red"]
    reset = COLORS["reset"]
    status = "SUCCESS" if success else "FAILED"

    print(f"{color}[  TOOLS   ] Result: {name} -> {status}{reset}", file=sys.stderr)

    # Show result summary
    if isinstance(result, dict):
        if "error" in result:
            print(f"{color}            Error: {result['error'][:100]}{reset}", file=sys.stderr)
        elif "result" in result:
            res = str(result["result"])[:100]
            print(f"{color}            Output: {res}...{reset}", file=sys.stderr)


def debug_message(role: str, content: str, has_tool_calls: bool = False):
    """Debug a conversation message."""
    if not DEBUG_ENABLED or not DEBUG_FLAGS.get("chat", False):
        return

    color = COLORS["cyan"]
    reset = COLORS["reset"]

    # Truncate content
    content_preview = content[:100] + "..." if len(content) > 100 else content
    content_preview = content_preview.replace('\n', '\\n')

    tool_info = " [+tool_calls]" if has_tool_calls else ""
    print(f"{color}[   CHAT   ] {role.upper()}: {content_preview}{tool_info}{reset}", file=sys.stderr)


def debug_stream_chunk(chunk_type: str, content: str = "", tool_name: str = ""):
    """Debug a streaming chunk."""
    if not DEBUG_ENABLED or not DEBUG_FLAGS.get("streaming", False):
        return

    color = COLORS["magenta"]
    reset = COLORS["reset"]

    if chunk_type == "content":
        # Only show if content is meaningful
        if content.strip():
            preview = content[:50].replace('\n', '\\n')
            print(f"{color}[STREAMING ] Content: {preview}{reset}", file=sys.stderr)
    elif chunk_type == "tool_start":
        print(f"{color}[STREAMING ] Tool starting: {tool_name}{reset}", file=sys.stderr)
    elif chunk_type == "tool_args":
        preview = content[:50] if content else ""
        print(f"{color}[STREAMING ] Tool args chunk: {preview}{reset}", file=sys.stderr)
    elif chunk_type == "done":
        print(f"{color}[STREAMING ] Stream complete{reset}", file=sys.stderr)


def debug_adapter(adapter_name: str, action: str, details: str = ""):
    """Debug adapter actions."""
    if not DEBUG_ENABLED or not DEBUG_FLAGS.get("adapters", False):
        return

    color = COLORS["blue"]
    reset = COLORS["reset"]

    print(f"{color}[ ADAPTERS ] {adapter_name}: {action}{reset}", file=sys.stderr)
    if details:
        print(f"{color}            {details}{reset}", file=sys.stderr)


def debug_api_request(endpoint: str, model: str, message_count: int, has_tools: bool):
    """Debug an API request."""
    if not DEBUG_ENABLED or not DEBUG_FLAGS.get("api", False):
        return

    color = COLORS["green"]
    reset = COLORS["reset"]

    tools_str = "with tools" if has_tools else "no tools"
    print(f"{color}[   API    ] Request -> {model} ({message_count} msgs, {tools_str}){reset}", file=sys.stderr)


def debug_api_response(has_content: bool, has_tool_calls: bool, finish_reason: str):
    """Debug an API response."""
    if not DEBUG_ENABLED or not DEBUG_FLAGS.get("api", False):
        return

    color = COLORS["green"]
    reset = COLORS["reset"]

    parts = []
    if has_content:
        parts.append("content")
    if has_tool_calls:
        parts.append("tool_calls")

    print(f"{color}[   API    ] Response <- [{', '.join(parts)}] finish={finish_reason}{reset}", file=sys.stderr)


def _print_data(data: Any, color: str, prefix: str, indent: int):
    """Print formatted data."""
    reset = COLORS["reset"]
    indent_str = "  " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{color}{prefix}{indent_str}{key}:{reset}", file=sys.stderr)
                _print_data(value, color, prefix, indent + 1)
            else:
                val_str = str(value)[:80]
                print(f"{color}{prefix}{indent_str}{key}: {val_str}{reset}", file=sys.stderr)
    elif isinstance(data, list):
        for i, item in enumerate(data[:5]):  # Limit to first 5 items
            if isinstance(item, (dict, list)):
                print(f"{color}{prefix}{indent_str}[{i}]:{reset}", file=sys.stderr)
                _print_data(item, color, prefix, indent + 1)
            else:
                item_str = str(item)[:80]
                print(f"{color}{prefix}{indent_str}[{i}]: {item_str}{reset}", file=sys.stderr)
        if len(data) > 5:
            print(f"{color}{prefix}{indent_str}... and {len(data) - 5} more{reset}", file=sys.stderr)
    else:
        data_str = str(data)[:200]
        print(f"{color}{prefix}{indent_str}{data_str}{reset}", file=sys.stderr)


# Convenience functions
def set_debug(enabled: bool):
    """Enable or disable all debug output."""
    global DEBUG_ENABLED
    DEBUG_ENABLED = enabled


def set_debug_category(category: str, enabled: bool):
    """Enable or disable a specific debug category."""
    if category in DEBUG_FLAGS:
        DEBUG_FLAGS[category] = enabled


def get_debug_status() -> Dict[str, bool]:
    """Get current debug status."""
    return {
        "enabled": DEBUG_ENABLED,
        "categories": DEBUG_FLAGS.copy(),
    }
