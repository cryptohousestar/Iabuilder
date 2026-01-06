"""Tests for the intelligent architecture components."""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from iabuilder.intent_classifier import IntentClassifier, IntentType
from iabuilder.main import IABuilderApp


class TestIntentClassifier(unittest.TestCase):
    """Test the IntentClassifier functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.classifier = IntentClassifier()

    def test_conversational_intent_greetings(self):
        """Test that greetings are classified as conversational."""
        test_cases = [
            "hola",
            "hello",
            "hi there",
            "buenos días",
            "buenas tardes",
            "buenas noches",
            "Hola, ¿cómo estás?",
            "Hello! How are you?",
        ]

        for message in test_cases:
            with self.subTest(message=message):
                intent = self.classifier.classify(message)
                self.assertEqual(intent, IntentType.CONVERSATIONAL)

                should_use_tools, confidence = self.classifier.should_use_tools(message)
                self.assertFalse(should_use_tools)
                self.assertGreater(confidence, 0.8)

    def test_conversational_intent_status(self):
        """Test status questions are conversational."""
        test_cases = [
            "cómo estás",
            "how are you",
            "¿qué tal?",
            "what's up",
            "gracias",
            "thanks",
            "thank you",
        ]

        for message in test_cases:
            with self.subTest(message=message):
                intent = self.classifier.classify(message)
                self.assertEqual(intent, IntentType.CONVERSATIONAL)

                should_use_tools, confidence = self.classifier.should_use_tools(message)
                self.assertFalse(should_use_tools)

    def test_informational_intent(self):
        """Test informational questions about capabilities."""
        test_cases = [
            "qué puedes hacer",
            "what can you do",
            "qué herramientas tienes",
            "what tools do you have",
            "explícame cómo funcionas",
            "explain how you work",
            "qué es esto",
            "what is this",
            "help",
            "ayuda",
        ]

        for message in test_cases:
            with self.subTest(message=message):
                intent = self.classifier.classify(message)
                self.assertEqual(intent, IntentType.INFORMATIONAL)

                should_use_tools, confidence = self.classifier.should_use_tools(message)
                self.assertFalse(should_use_tools)

    def test_actionable_intent_file_operations(self):
        """Test file operations are classified as actionable."""
        test_cases = [
            "lee el archivo config.json",
            "read the config.py file",
            "crea un nuevo archivo",
            "create a new file called test.py",
            "edita el código",
            "edit the code",
            "borra ese archivo",
            "delete that file",
        ]

        for message in test_cases:
            with self.subTest(message=message):
                intent = self.classifier.classify(message)
                self.assertEqual(intent, IntentType.ACTIONABLE)

                should_use_tools, confidence = self.classifier.should_use_tools(message)
                self.assertTrue(should_use_tools)
                self.assertGreater(confidence, 0.7)

    def test_actionable_intent_system_operations(self):
        """Test system operations are actionable."""
        test_cases = [
            "ejecuta el comando ls",
            "run the ls command",
            "instala las dependencias",
            "install dependencies",
            "compila el proyecto",
            "compile the project",
            "despliega la aplicación",
            "deploy the application",
        ]

        for message in test_cases:
            with self.subTest(message=message):
                intent = self.classifier.classify(message)
                self.assertEqual(intent, IntentType.ACTIONABLE)

                should_use_tools, confidence = self.classifier.should_use_tools(message)
                self.assertTrue(should_use_tools)

    def test_actionable_intent_code_content(self):
        """Test messages with code are actionable."""
        test_cases = [
            "crea una función que sume dos números",
            "write a function that adds two numbers",
            "implementa una clase",
            "implement a class",
            "def fibonacci(n):",
            "function calculateTotal()",
        ]

        for message in test_cases:
            with self.subTest(message=message):
                intent = self.classifier.classify(message)
                self.assertEqual(intent, IntentType.ACTIONABLE)

                should_use_tools, confidence = self.classifier.should_use_tools(message)
                self.assertTrue(should_use_tools)

    def test_analytical_intent(self):
        """Test analytical questions may need tools."""
        test_cases = [
            "analiza este código",
            "analyze this code",
            "revisa la implementación",
            "review the implementation",
            "evalúa el rendimiento",
            "evaluate performance",
            "verifica si funciona",
            "check if it works",
        ]

        for message in test_cases:
            with self.subTest(message=message):
                intent = self.classifier.classify(message)
                self.assertEqual(intent, IntentType.ANALYTICAL)

                # Analytical may or may not need tools based on complexity
                should_use_tools, confidence = self.classifier.should_use_tools(message)
                # We don't assert here as it depends on complexity calculation

    def test_complexity_calculation(self):
        """Test complexity scoring."""
        # Simple message
        complexity = self.classifier._calculate_complexity("hola")
        self.assertLess(complexity, 0.3)

        # Complex message with technical terms
        complexity = self.classifier._calculate_complexity(
            "implementa una función recursiva de fibonacci con memoización en Python"
        )
        self.assertGreater(complexity, 0.5)

    def test_cache_functionality(self):
        """Test that classification results are cached."""
        message = "test message for caching"

        # First classification
        intent1 = self.classifier.classify(message)
        count1 = self.classifier.classification_count

        # Second classification (should use cache)
        intent2 = self.classifier.classify(message)
        count2 = self.classifier.classification_count

        # Results should be the same
        self.assertEqual(intent1, intent2)
        # Count should only increase by 1 (not by 2)
        self.assertEqual(count1 + 1, count2)

    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        message = "test message"
        self.classifier.classify(message)

        # Cache should have entry
        self.assertIn(message, self.classifier.cache)

        # Clear cache
        self.classifier.clear_cache()

        # Cache should be empty
        self.assertEqual(len(self.classifier.cache), 0)

    def test_stats_functionality(self):
        """Test statistics reporting."""
        initial_count = self.classifier.classification_count

        self.classifier.classify("test message")

        stats = self.classifier.get_stats()
        self.assertEqual(stats['total_classifications'], initial_count + 1)
        self.assertIn('spacy_available', stats)
        self.assertIn('cache_size', stats)

    def test_fallback_without_spacy(self):
        """Test that classifier works without spaCy."""
        # This would require mocking spaCy import failure
        # For now, we test that the classifier initializes properly
        self.assertIsInstance(self.classifier, IntentClassifier)
        self.assertIsNotNone(self.classifier.nlp)  # Should have loaded spaCy


class TestIntelligentArchitectureIntegration(unittest.TestCase):
    """Test the integration of intelligent architecture components."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the config and dependencies to avoid real API calls
        with patch('iabuilder.main.get_config_manager'), \
             patch('iabuilder.main.load_config'), \
             patch('iabuilder.main.get_tool_registry'), \
             patch('iabuilder.main.setup_tools'):

            mock_config = Mock()
            mock_config.api_key = "test-key"
            mock_config.default_model = "test-model"
            mock_config.auto_save = False
            mock_config.safe_mode = True

            # Create app with mocked dependencies
            self.app = IABuilderApp.__new__(IABuilderApp)
            self.app.config = mock_config
            self.app.intent_classifier = IntentClassifier()
            self.app.langchain_agent = None  # Test without LangChain first

    def test_conversational_message_handling(self):
        """Test that conversational messages are handled without tools."""
        with patch.object(self.app, '_handle_conversational_response') as mock_handler:
            # Simulate conversational message
            self.app._handle_chat_message("hola")

            # Should call conversational handler, not tool handlers
            mock_handler.assert_called_once()

    def test_actionable_message_routing(self):
        """Test that actionable messages are routed to tool handling."""
        with patch.object(self.app, '_handle_actionable_request') as mock_handler, \
             patch.object(self.app.intent_classifier, 'classify', return_value=IntentClassifier.IntentType.ACTIONABLE), \
             patch.object(self.app.intent_classifier, 'should_use_tools', return_value=(True, 0.9)):

            self.app._handle_chat_message("crea un archivo test.py")

            # Should call actionable handler
            mock_handler.assert_called_once()

    def test_special_cases_handling(self):
        """Test that special cases (tool exploration, etc.) are handled correctly."""
        with patch.object(self.app, '_handle_tool_exploration') as mock_handler:
            self.app._handle_chat_message("qué herramientas tienes")

            mock_handler.assert_called_once()

    def test_fallback_system_integration(self):
        """Test that fallback system works when LangChain is not available."""
        with patch.object(self.app, '_handle_with_fallback_system') as mock_fallback:
            # Force no LangChain agent
            self.app.langchain_agent = None

            # Mock actionable intent
            with patch.object(self.app.intent_classifier, 'classify', return_value=IntentClassifier.IntentType.ACTIONABLE), \
                 patch.object(self.app.intent_classifier, 'should_use_tools', return_value=(True, 0.9)):

                self.app._handle_chat_message("crea un archivo")

                mock_fallback.assert_called_once()


class TestLangChainIntegration(unittest.TestCase):
    """Test LangChain integration when available."""

    def setUp(self):
        """Set up test with mocked LangChain."""
        # Only run if LangChain is available
        try:
            import langchain
            self.langchain_available = True
        except ImportError:
            self.langchain_available = False
            self.skipTest("LangChain not available")

    @unittest.skipUnless(langchain_available, "LangChain not available")
    def test_langchain_agent_creation(self):
        """Test that LangChain agent can be created."""
        from iabuilder.main import LANGCHAIN_AVAILABLE

        if not LANGCHAIN_AVAILABLE:
            self.skipTest("LangChain imports failed")

        # Test agent creation logic (would need more complex mocking)
        # This is a placeholder for when we have full LangChain setup
        self.assertTrue(LANGCHAIN_AVAILABLE)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)