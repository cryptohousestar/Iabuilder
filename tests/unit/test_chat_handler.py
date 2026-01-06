"""Tests for chat.handler module."""

import unittest
from unittest.mock import Mock, MagicMock

from iabuilder.chat.handler import ChatHandler
from iabuilder.intent_classifier import IntentType


class TestChatHandler(unittest.TestCase):
    """Test ChatHandler class."""

    def setUp(self):
        """Set up test environment."""
        self.mock_conversation = Mock()
        self.mock_renderer = Mock()
        self.handler = ChatHandler(self.mock_conversation, self.mock_renderer)

    def test_initialization(self):
        """Test chat handler initialization."""
        self.assertIsNotNone(self.handler.conversation)
        self.assertIsNotNone(self.handler.renderer)
        self.assertIsNotNone(self.handler.error_handler)
        self.assertIsNotNone(self.handler.intent_classifier)

    def test_handle_greeting(self):
        """Test handling greeting messages."""
        greetings = ["hola", "hello", "hi", "buenos días"]

        for greeting in greetings:
            result = self.handler.handle_message(greeting)
            self.assertTrue(result)
            self.mock_conversation.add_message.assert_called()

    def test_handle_non_greeting(self):
        """Test handling non-greeting messages."""
        message = "create a file called test.py"
        result = self.handler.handle_message(message)

        # Should return False to indicate further processing needed
        self.assertFalse(result)

    def test_classify_intent_conversational(self):
        """Test intent classification for conversational messages."""
        message = "hello how are you"
        intent, confidence, should_use_tools = self.handler.classify_intent(message)

        self.assertIsInstance(intent, IntentType)
        self.assertIsInstance(confidence, float)
        self.assertIsInstance(should_use_tools, bool)

    def test_classify_intent_actionable(self):
        """Test intent classification for actionable messages."""
        message = "create a file called test.py with hello world"
        intent, confidence, should_use_tools = self.handler.classify_intent(message)

        self.assertIsInstance(intent, IntentType)
        self.assertTrue(should_use_tools)

    def test_is_greeting_detection(self):
        """Test greeting detection."""
        self.assertTrue(self.handler._is_greeting("hola"))
        self.assertTrue(self.handler._is_greeting("hello there"))
        self.assertTrue(self.handler._is_greeting("buenos días"))
        self.assertFalse(self.handler._is_greeting("create a file"))

    def test_is_tool_query_detection(self):
        """Test tool query detection."""
        self.assertTrue(self.handler._is_tool_query("qué herramientas tienes"))
        self.assertTrue(self.handler._is_tool_query("what tools available"))
        self.assertTrue(self.handler._is_tool_query("qué puedes hacer"))
        self.assertFalse(self.handler._is_tool_query("create a file"))

    def test_respond_greeting_spanish(self):
        """Test Spanish greeting response."""
        self.handler._respond_greeting("buenos días")
        self.mock_conversation.add_message.assert_called()
        self.mock_renderer.render_assistant_message.assert_called()

    def test_respond_greeting_english(self):
        """Test English greeting response."""
        self.handler._respond_greeting("hello")
        self.mock_conversation.add_message.assert_called()
        self.mock_renderer.render_assistant_message.assert_called()

    def test_conversational_response_status(self):
        """Test conversational response for status questions."""
        self.handler.handle_conversational_response("cómo estás")
        self.mock_conversation.add_message.assert_called()
        self.mock_renderer.render_assistant_message.assert_called()

    def test_conversational_response_thanks(self):
        """Test conversational response for thanks."""
        self.handler.handle_conversational_response("gracias")
        self.mock_conversation.add_message.assert_called()

    def test_conversational_response_farewell(self):
        """Test conversational response for farewell."""
        self.handler.handle_conversational_response("adiós")
        self.mock_conversation.add_message.assert_called()

    def test_conversational_response_default(self):
        """Test default conversational response."""
        self.handler.handle_conversational_response("random message")
        self.mock_conversation.add_message.assert_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
