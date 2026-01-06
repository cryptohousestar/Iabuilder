"""Chat message handling for IABuilder."""

from typing import Optional, Tuple
from ..intent_classifier import IntentClassifier, IntentType
from ..renderer import Renderer
from ..errors import get_error_handler


class ChatHandler:
    """Handles chat messages and routes them appropriately."""

    def __init__(self, conversation, renderer: Optional[Renderer] = None):
        """Initialize chat handler.

        Args:
            conversation: Conversation manager
            renderer: Renderer for output
        """
        self.conversation = conversation
        self.renderer = renderer or Renderer()
        self.error_handler = get_error_handler()
        self.intent_classifier = IntentClassifier()

    def handle_message(self, message: str) -> bool:
        """Handle a chat message.

        Args:
            message: User message to process

        Returns:
            True if handled, False if needs further processing
        """
        try:
            # Add user message to conversation
            self.conversation.add_message("user", message)

            # Check for special cases
            if self._handle_special_cases(message):
                return True

            return False

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={"message": message[:100]}
            )
            return False

    def classify_intent(self, message: str) -> Tuple[IntentType, float, bool]:
        """Classify message intent.

        Args:
            message: Message to classify

        Returns:
            Tuple of (intent_type, confidence, should_use_tools)
        """
        try:
            intent = self.intent_classifier.classify(message)
            should_use_tools, confidence = self.intent_classifier.should_use_tools(message)

            self.renderer.render_info(
                f"🤖 Intent: {intent.value} (confidence: {confidence:.2f})"
            )

            return intent, confidence, should_use_tools

        except Exception as e:
            self.error_handler.log_warning(
                f"Intent classification failed: {e}"
            )
            # Default to actionable with tools
            return IntentType.ACTIONABLE, 0.5, True

    def _handle_special_cases(self, message: str) -> bool:
        """Handle special cases like greetings, tool exploration, etc.

        Args:
            message: User message

        Returns:
            True if handled, False otherwise
        """
        message_lower = message.lower()

        # Greetings
        if self._is_greeting(message_lower):
            self._respond_greeting(message_lower)
            return True

        # Tool exploration
        if self._is_tool_query(message_lower):
            return False  # Will be handled by app

        return False

    def _is_greeting(self, message: str) -> bool:
        """Check if message is ONLY a greeting (not part of a longer request).

        Only matches short messages that are primarily greetings.
        """
        message = message.strip().lower()

        # Must be a short message (less than 30 chars) to be just a greeting
        if len(message) > 30:
            return False

        # Exact or near-exact greeting matches
        exact_greetings = [
            "hola", "hello", "hi", "hey", "ey",
            "buenos dias", "buenos días", "buen dia", "buen día",
            "buenas tardes", "buenas noches",
            "hola!", "hello!", "hi!", "hey!",
            "hola?", "que tal", "qué tal", "como andas",
            "hola, como estas", "hola como estas",
            "hola, cómo estás", "hola cómo estás",
        ]

        # Check for exact match (with or without punctuation)
        clean_message = message.rstrip("?!.,")
        if clean_message in exact_greetings:
            return True

        # Check if message starts with greeting and is short
        greeting_starters = ["hola", "hello", "hi ", "hey ", "buenos", "buenas"]
        if len(message) < 20:
            for starter in greeting_starters:
                if message.startswith(starter) and not any(
                    action in message for action in
                    ["podes", "puedes", "podrias", "podrías", "quiero", "necesito",
                     "ejecuta", "crea", "abre", "lee", "escribe", "busca", "muestra"]
                ):
                    return True

        return False

    def _is_tool_query(self, message: str) -> bool:
        """Check if message is asking about tools."""
        tool_queries = [
            "qué herramientas", "que herramientas",
            "herramientas tienes", "tools available",
            "qué puedes hacer", "que puedes hacer"
        ]
        return any(query in message for query in tool_queries)

    def _respond_greeting(self, message: str):
        """Respond to greeting messages."""
        if "buenos dias" in message or "buenos días" in message:
            response = "¡Buenos días! ☀️ ¿En qué proyecto estás trabajando?"
        elif "buenas tardes" in message:
            response = "¡Buenas tardes! 🌅 ¿Cómo puedo asistirte?"
        elif "buenas noches" in message:
            response = "¡Buenas noches! 🌙 ¿Qué necesitas?"
        else:
            response = "¡Hola! 👋 ¿En qué puedo ayudarte hoy?"

        self.conversation.add_message("assistant", response)
        self.renderer.render_assistant_message(response)

    def handle_conversational_response(self, message: str):
        """Handle conversational messages without tools."""
        message_lower = message.lower().strip()

        # Status questions
        if any(status in message_lower for status in ["cómo estás", "como estas", "how are you"]):
            response = "¡Estoy funcionando perfectamente! 🚀 Tengo acceso a herramientas inteligentes para ayudarte con tu proyecto."

        # Thanks
        elif any(thanks in message_lower for thanks in ["gracias", "thanks", "thank you"]):
            response = "¡De nada! 😊 Estoy aquí para ayudarte cuando lo necesites."

        # Farewell
        elif any(bye in message_lower for bye in ["adiós", "adios", "bye", "chau", "hasta luego"]):
            response = "¡Hasta luego! 👋 ¡Que tengas un excelente día!"

        # Default
        else:
            response = "¡Entiendo! ¿En qué puedo ayudarte específicamente? Puedo crear archivos, ejecutar comandos, analizar código, o cualquier tarea de desarrollo que necesites."

        self.conversation.add_message("assistant", response)
        self.renderer.render_assistant_message(response)
