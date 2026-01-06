"""Tools for IABuilder - 5 essential tools."""

from typing import List

from .base import Tool, ToolRegistry, get_tool_registry, register_tool
from .bash import BashTool
from .file_ops import EditFileTool, ReadFileTool, WriteFileTool
from .web_search import WebSearchTool


def setup_tools(safe_mode: bool = True) -> int:
    """Setup the 5 essential tools.

    Args:
        safe_mode: Enable safe mode for bash operations

    Returns:
        Number of tools registered
    """
    tools = [
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool(),
        BashTool(safe_mode=safe_mode),
        WebSearchTool(),
    ]

    for tool in tools:
        register_tool(tool)

    print(f"🧰 Registered {len(tools)} tools: read_file, write_file, edit_file, execute_bash, web_search")

    return len(tools)


__all__ = [
    "Tool",
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
    "setup_tools",
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "BashTool",
    "WebSearchTool",
]
