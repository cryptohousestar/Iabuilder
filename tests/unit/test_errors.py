"""Tests for errors module."""

import unittest
import tempfile
import os
from pathlib import Path

from iabuilder.errors import (
    IABuilderError,
    ToolError,
    APIError,
    ConfigError,
    ValidationError,
    ProviderError,
    ErrorHandler,
    get_error_handler,
)


class TestExceptions(unittest.TestCase):
    """Test custom exceptions."""

    def test_iabuilder_error(self):
        """Test base IABuilderError."""
        error = IABuilderError("Test error")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Test error")

    def test_tool_error(self):
        """Test ToolError."""
        original = ValueError("Original error")
        error = ToolError("bash", "Command failed", original)

        self.assertEqual(error.tool_name, "bash")
        self.assertEqual(error.original_error, original)
        self.assertIn("bash", str(error))

    def test_api_error(self):
        """Test APIError."""
        error = APIError("groq", "Rate limited", status_code=429)

        self.assertEqual(error.provider, "groq")
        self.assertEqual(error.status_code, 429)
        self.assertIn("groq", str(error))

    def test_config_error(self):
        """Test ConfigError."""
        error = ConfigError("Invalid config", config_file="config.yaml")

        self.assertEqual(error.config_file, "config.yaml")
        self.assertIn("Invalid config", str(error))

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("api_key", "Key too short")

        self.assertEqual(error.field, "api_key")
        self.assertIn("api_key", str(error))

    def test_provider_error(self):
        """Test ProviderError."""
        error = ProviderError("openai", "Not configured")

        self.assertEqual(error.provider, "openai")
        self.assertIn("openai", str(error))


class TestErrorHandler(unittest.TestCase):
    """Test ErrorHandler class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
        self.handler = ErrorHandler(log_dir=self.log_dir)

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test error handler initialization."""
        self.assertIsNotNone(self.handler.logger)
        self.assertTrue(self.log_dir.exists())

    def test_handle_error_without_raise(self):
        """Test handling error without raising."""
        error = ValueError("Test error")
        result = self.handler.handle_error(error, raise_error=False)

        self.assertIsInstance(result, str)
        self.assertIn("ValueError", result)
        self.assertIn("Test error", result)

    def test_handle_error_with_raise(self):
        """Test handling error with raising."""
        error = ValueError("Test error")

        with self.assertRaises(ValueError):
            self.handler.handle_error(error, raise_error=True)

    def test_handle_error_with_context(self):
        """Test handling error with context."""
        error = ValueError("Test error")
        context = {"operation": "test", "user": "test_user"}

        result = self.handler.handle_error(error, context=context)
        self.assertIsNotNone(result)

    def test_handle_tool_error(self):
        """Test handling tool error."""
        error = Exception("Tool failed")
        tool_args = {"command": "ls -la"}

        result = self.handler.handle_tool_error("bash", error, tool_args)

        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["tool_name"], "bash")

    def test_handle_api_error_rate_limit(self):
        """Test handling rate limit error."""
        error = APIError("groq", "Rate limit 429", status_code=429)

        result = self.handler.handle_api_error("groq", error)

        self.assertIn("Rate limit", result)
        self.assertIn("groq", result)

    def test_handle_api_error_auth(self):
        """Test handling authentication error."""
        error = APIError("groq", "Invalid API key 401", status_code=401)

        result = self.handler.handle_api_error("groq", error)

        self.assertIn("API key", result)
        self.assertIn("groq", result)

    def test_handle_api_error_timeout(self):
        """Test handling timeout error."""
        error = Exception("Request timeout")

        result = self.handler.handle_api_error("groq", error)

        self.assertIn("Timeout", result)

    def test_handle_api_error_generic(self):
        """Test handling generic API error."""
        error = Exception("Unknown error")

        result = self.handler.handle_api_error("groq", error)

        self.assertIn("Error de API", result)

    def test_log_info(self):
        """Test logging info message."""
        # Should not raise exception
        self.handler.log_info("Test info message")
        self.handler.log_info("Test with context", {"key": "value"})

    def test_log_warning(self):
        """Test logging warning message."""
        # Should not raise exception
        self.handler.log_warning("Test warning")

    def test_log_debug(self):
        """Test logging debug message."""
        # Should not raise exception
        self.handler.log_debug("Test debug")

    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns singleton."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()

        self.assertIs(handler1, handler2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
