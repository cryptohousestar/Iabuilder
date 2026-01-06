"""Custom exceptions for IABuilder."""


class IABuilderError(Exception):
    """Base exception for IABuilder."""
    pass


class ToolError(IABuilderError):
    """Error executing a tool."""

    def __init__(self, tool_name: str, message: str, original_error: Exception = None):
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(f"Tool '{tool_name}': {message}")


class APIError(IABuilderError):
    """Error calling API."""

    def __init__(self, provider: str, message: str, status_code: int = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"API Error ({provider}): {message}")


class ConfigError(IABuilderError):
    """Error in configuration."""

    def __init__(self, message: str, config_file: str = None):
        self.config_file = config_file
        super().__init__(f"Config Error: {message}")


class ValidationError(IABuilderError):
    """Error validating input."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validation Error ({field}): {message}")


class ProviderError(IABuilderError):
    """Error with provider configuration or execution."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"Provider Error ({provider}): {message}")
