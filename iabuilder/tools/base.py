"""Base classes and registry for tools (function calling)."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class Tool(ABC):
    """Abstract base class for tools."""

    def __init__(self):
        """Initialize tool."""
        self.name = self._get_name()
        self.description = self._get_description()
        self.parameters = self._get_parameters()

    @abstractmethod
    def _get_name(self) -> str:
        """Get tool name.

        Returns:
            Tool name
        """
        pass

    @abstractmethod
    def _get_description(self) -> str:
        """Get tool description.

        Returns:
            Tool description
        """
        pass

    @abstractmethod
    def _get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema (JSON Schema format).

        Returns:
            Parameters schema dictionary
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given arguments.

        Args:
            **kwargs: Tool arguments

        Returns:
            Dictionary with execution result
        """
        pass

    def to_function_schema(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling schema.

        Returns:
            Function schema dictionary
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registry for managing and executing tools."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool.

        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool

    def unregister(self, name: str):
        """Unregister a tool.

        Args:
            name: Tool name to unregister
        """
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get function schemas for all registered tools.

        Returns:
            List of function schema dictionaries
        """
        return [tool.to_function_schema() for tool in self._tools.values()]

    def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name.

        Args:
            name: Tool name
            **kwargs: Tool arguments

        Returns:
            Dictionary with execution result

        Raises:
            ValueError: If tool not found
        """
        tool = self.get(name)
        if tool is None:
            # Debug: Show available tools
            available = list(self._tools.keys())
            print(f"[DEBUG] Tool '{name}' not found. Available tools: {available}")
            return {
                "success": False,
                "error": f"Tool '{name}' not found. Available: {available}",
            }

        try:
            result = tool.execute(**kwargs)
            return {
                "success": True,
                **result,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }


# Global tool registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create global tool registry instance.

    Returns:
        ToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(tool: Tool):
    """Convenience function to register a tool.

    Args:
        tool: Tool instance to register
    """
    get_tool_registry().register(tool)
