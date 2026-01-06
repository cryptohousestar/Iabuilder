"""Centralized error handling for IABuilder."""

import logging
import traceback
from pathlib import Path
from typing import Optional, Any

from .exceptions import (
    IABuilderError,
    ToolError,
    APIError,
    ConfigError,
    ValidationError,
    ProviderError,
)


class ErrorHandler:
    """Centralized error handler with logging."""

    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize error handler.

        Args:
            log_dir: Directory for log files (defaults to ~/.iabuilder/logs)
        """
        if log_dir is None:
            log_dir = Path.home() / ".iabuilder" / "logs"

        log_dir.mkdir(parents=True, exist_ok=True)

        # Configure logging
        self.logger = logging.getLogger("iabuilder")
        self.logger.setLevel(logging.DEBUG)

        # File handler (detailed logs)
        file_handler = logging.FileHandler(log_dir / "iabuilder.log")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler (errors only)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def handle_error(
        self,
        error: Exception,
        context: dict = None,
        raise_error: bool = False
    ) -> Optional[str]:
        """Handle an error with logging and optional re-raising.

        Args:
            error: The exception to handle
            context: Additional context information
            raise_error: Whether to re-raise the exception

        Returns:
            Error message string if not raising, None otherwise
        """
        context = context or {}

        # Log the error
        error_msg = str(error)
        error_type = type(error).__name__

        self.logger.error(
            f"{error_type}: {error_msg}",
            extra=context,
            exc_info=True
        )

        # Re-raise if requested
        if raise_error:
            raise error

        return f"{error_type}: {error_msg}"

    def handle_tool_error(
        self,
        tool_name: str,
        error: Exception,
        tool_args: dict = None
    ) -> dict:
        """Handle tool execution errors.

        Args:
            tool_name: Name of the tool that failed
            error: The exception that occurred
            tool_args: Tool arguments that were used

        Returns:
            Error result dictionary
        """
        context = {
            "tool_name": tool_name,
            "tool_args": tool_args or {}
        }

        error_msg = self.handle_error(error, context)

        return {
            "success": False,
            "error": error_msg,
            "error_type": type(error).__name__,
            "tool_name": tool_name
        }

    def handle_api_error(
        self,
        provider: str,
        error: Exception,
        request_data: dict = None
    ) -> str:
        """Handle API call errors.

        Args:
            provider: Name of the API provider
            error: The exception that occurred
            request_data: Data that was sent in the request

        Returns:
            User-friendly error message
        """
        context = {
            "provider": provider,
            "request_data": request_data or {}
        }

        # Check for specific error types
        error_msg = str(error)

        if "rate limit" in error_msg.lower() or "429" in error_msg:
            user_msg = f"⚠️  Rate limit alcanzado en {provider}. Esperando 60s..."
            self.logger.warning(user_msg, extra=context)
            return user_msg

        elif "api key" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
            user_msg = f"❌ API key inválida para {provider}. Verifica tu configuración."
            self.logger.error(user_msg, extra=context)
            return user_msg

        elif "timeout" in error_msg.lower():
            user_msg = f"⏱️  Timeout en {provider}. Reintentando..."
            self.logger.warning(user_msg, extra=context)
            return user_msg

        else:
            user_msg = f"❌ Error de API en {provider}: {error_msg}"
            self.logger.error(user_msg, extra=context, exc_info=True)
            return user_msg

    def log_info(self, message: str, context: dict = None):
        """Log informational message."""
        self.logger.info(message, extra=context or {})

    def log_warning(self, message: str, context: dict = None):
        """Log warning message."""
        self.logger.warning(message, extra=context or {})

    def log_debug(self, message: str, context: dict = None):
        """Log debug message."""
        self.logger.debug(message, extra=context or {})


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler
