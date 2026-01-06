"""Tests for ai.response_processor module."""

import unittest
import json
from unittest.mock import Mock, MagicMock, patch

from iabuilder.ai.response_processor import ResponseProcessor, RetryHandler


class TestResponseProcessor(unittest.TestCase):
    """Test ResponseProcessor class."""

    def setUp(self):
        """Set up test environment."""
        self.mock_conversation = Mock()
        self.mock_renderer = Mock()
        self.processor = ResponseProcessor(self.mock_conversation, self.mock_renderer)

    def test_initialization(self):
        """Test processor initialization."""
        self.assertIsNotNone(self.processor.conversation)
        self.assertIsNotNone(self.processor.renderer)
        self.assertIsNotNone(self.processor.error_handler)
        self.assertIsNotNone(self.processor.tool_registry)

    def test_has_tool_calls_true(self):
        """Test detection of tool calls in response."""
        mock_response = Mock()
        mock_response.tool_calls = [Mock()]

        result = self.processor._has_tool_calls(mock_response)
        self.assertTrue(result)

    def test_has_tool_calls_false(self):
        """Test detection when no tool calls."""
        mock_response = Mock()
        mock_response.tool_calls = []

        result = self.processor._has_tool_calls(mock_response)
        self.assertFalse(result)

    def test_has_tool_calls_no_attribute(self):
        """Test detection when response has no tool_calls attribute."""
        mock_response = Mock(spec=[])

        result = self.processor._has_tool_calls(mock_response)
        self.assertFalse(result)

    def test_extract_content_success(self):
        """Test content extraction from response."""
        mock_message = Mock()
        mock_message.content = "Test response content"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]

        result = self.processor._extract_content(mock_response)
        self.assertEqual(result, "Test response content")

    def test_extract_content_empty(self):
        """Test content extraction when empty."""
        mock_response = Mock()
        mock_response.choices = []

        result = self.processor._extract_content(mock_response)
        self.assertEqual(result, "")

    def test_parse_args_success(self):
        """Test parsing tool call arguments."""
        mock_tool_call = Mock()
        mock_tool_call.function.arguments = '{"key": "value"}'

        result = self.processor._parse_args(mock_tool_call)
        self.assertEqual(result, {"key": "value"})

    def test_parse_args_invalid_json(self):
        """Test parsing invalid JSON arguments."""
        mock_tool_call = Mock()
        mock_tool_call.function.arguments = 'invalid json'

        result = self.processor._parse_args(mock_tool_call)
        self.assertEqual(result, {})

    def test_execute_tool_call_success(self):
        """Test successful tool execution."""
        mock_tool_call = Mock()
        mock_tool_call.function.name = "test_tool"
        mock_tool_call.function.arguments = '{"arg": "value"}'

        with patch.object(self.processor.tool_registry, 'execute') as mock_execute:
            mock_execute.return_value = {"success": True, "result": "done"}

            result = self.processor._execute_tool_call(mock_tool_call)

            self.assertTrue(result["success"])
            mock_execute.assert_called_once_with("test_tool", arg="value")

    def test_execute_tool_call_failure(self):
        """Test tool execution failure."""
        mock_tool_call = Mock()
        mock_tool_call.function.name = "test_tool"
        mock_tool_call.function.arguments = '{"arg": "value"}'

        with patch.object(self.processor.tool_registry, 'execute') as mock_execute:
            mock_execute.side_effect = Exception("Tool failed")

            result = self.processor._execute_tool_call(mock_tool_call)

            self.assertFalse(result["success"])
            self.assertIn("error", result)

    def test_process_response_without_tools(self):
        """Test processing response without tool calls."""
        mock_message = Mock()
        mock_message.content = "Simple response"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.tool_calls = []

        with patch.object(self.processor, '_has_tool_calls', return_value=False):
            result = self.processor.process_response(mock_response)

            self.assertEqual(result, "Simple response")


class TestRetryHandler(unittest.TestCase):
    """Test RetryHandler class."""

    def setUp(self):
        """Set up test environment."""
        self.handler = RetryHandler(max_retries=2, base_delay=0.1)

    def test_initialization(self):
        """Test retry handler initialization."""
        self.assertEqual(self.handler.max_retries, 2)
        self.assertEqual(self.handler.base_delay, 0.1)

    def test_call_with_retry_success_first_try(self):
        """Test successful call on first try."""
        mock_func = Mock(return_value="success")

        result = self.handler.call_with_retry(mock_func, "arg1", key="value")

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 1)

    def test_call_with_retry_success_after_retries(self):
        """Test successful call after retries."""
        mock_func = Mock(side_effect=[
            Exception("First fail"),
            Exception("Second fail"),
            "success"
        ])

        with patch('time.sleep'):  # Mock sleep to speed up test
            result = self.handler.call_with_retry(mock_func)

            self.assertEqual(result, "success")
            self.assertEqual(mock_func.call_count, 3)

    def test_call_with_retry_all_fail(self):
        """Test when all retries fail."""
        mock_func = Mock(side_effect=Exception("Always fails"))

        with patch('time.sleep'):
            with self.assertRaises(Exception) as context:
                self.handler.call_with_retry(mock_func)

            self.assertIn("Always fails", str(context.exception))
            self.assertEqual(mock_func.call_count, 3)  # Initial + 2 retries

    def test_call_with_retry_rate_limit(self):
        """Test retry with rate limit error."""
        mock_func = Mock(side_effect=[
            Exception("Rate limit exceeded 429"),
            "success"
        ])

        with patch('time.sleep') as mock_sleep:
            result = self.handler.call_with_retry(mock_func)

            self.assertEqual(result, "success")
            # Check that sleep was called with longer delay for rate limit
            mock_sleep.assert_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
