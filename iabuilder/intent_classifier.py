"""Intelligent Intent Classification using spaCy for Spanish text analysis."""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

try:
    import spacy
    from spacy.lang.es import Spanish
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None
    Spanish = None

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of user intents that the classifier can identify."""
    CONVERSATIONAL = "conversational"  # Greetings, questions about capabilities
    INFORMATIONAL = "informational"    # Questions about how things work
    ACTIONABLE = "actionable"         # Requests to perform actions
    ANALYTICAL = "analytical"         # Analysis requests (may need tools)
    UNKNOWN = "unknown"              # Cannot classify


class IntentClassifier:
    """Intelligent classifier for user message intents using spaCy.

    This classifier uses a hybrid approach combining:
    - Rule-based patterns for high-precision classification
    - spaCy NLP for understanding Spanish text structure
    - Confidence scoring for decision making
    """

    def __init__(self, model_name: str = "es_core_news_sm"):
        """Initialize the intent classifier.

        Args:
            model_name: spaCy model to use for Spanish text processing
        """
        self.model_name = model_name
        self.nlp = None
        self._initialize_spacy()

        # Classification patterns
        self._setup_patterns()

        # Performance metrics
        self.classification_count = 0
        self.cache = {}  # Simple cache for repeated messages

    def _initialize_spacy(self):
        """Initialize spaCy model with error handling."""
        if not SPACY_AVAILABLE:
            logger.warning("spaCy not available. Using fallback classification.")
            return

        try:
            self.nlp = spacy.load(self.model_name)
            logger.info(f"spaCy model '{self.model_name}' loaded successfully")
        except OSError as e:
            logger.warning(f"Could not load spaCy model '{self.model_name}': {e}")
            logger.info("Attempting to download model...")
            try:
                import subprocess
                subprocess.run([
                    "python", "-m", "spacy", "download", self.model_name
                ], check=True, capture_output=True)
                self.nlp = spacy.load(self.model_name)
                logger.info("spaCy model downloaded and loaded successfully")
            except Exception as download_error:
                logger.error(f"Failed to download spaCy model: {download_error}")
                logger.warning("Using rule-based fallback classification")
        except Exception as e:
            logger.error(f"Unexpected error loading spaCy: {e}")
            logger.warning("Using rule-based fallback classification")

    def _setup_patterns(self):
        """Setup regex patterns and keyword lists for classification."""
        # Conversational patterns (never need tools)
        self.conversational_patterns = [
            # Greetings
            re.compile(r'^(hola|hello|hi|hey|buenos?\s+dias|buenas?\s+(tardes|noches))$', re.IGNORECASE),
            re.compile(r'^(adiós|bye|goodbye|chau|nos\s+vemos|hasta\s+luego)$', re.IGNORECASE),

            # Status questions
            re.compile(r'^(cómo\s+estás?|how\s+are\s+you|qué\s+tal|what\'s\s+up)$', re.IGNORECASE),
            re.compile(r'^(gracias|thanks|thank\s+you)$', re.IGNORECASE),

            # Pure conversation
            re.compile(r'^(sí|no|yes|no|ok|okay|claro|por\s+supuesto|entiendo|vale|de\s+acuerdo)$', re.IGNORECASE),
        ]

        # Informational patterns (questions about system/capabilities)
        self.informational_keywords = {
            "qué puedes hacer", "que puedes hacer", "what can you do",
            "qué eres", "que eres", "what are you",
            "cómo funcionas", "como funcionas", "how do you work",
            "qué herramientas", "que herramientas", "what tools",
            "explícame", "explain", "dime", "tell me",
            "cuéntame", "describe", "qué es", "what is",
            "ayuda", "help", "soporte", "support",
            "manual", "guía", "guide", "tutorial",
        }

        # Actionable keywords (definitely need tools)
        self.actionable_verbs = [
            # File operations
            "lee", "leer", "read", "abre", "abrir", "open", "muestra", "show", "ver", "ve",
            "crea", "crear", "create", "escribe", "escribir", "write",
            "edita", "editar", "edit", "modifica", "modify", "cambia", "change",
            "elimina", "eliminar", "delete", "borra", "borrar", "remove",
            "renombra", "rename", "mueve", "move", "copia", "copy",

            # System operations
            "ejecuta", "ejecutar", "run", "corre", "correr", "execute",
            "instala", "instalar", "install", "compila", "compilar", "compile",
            "despliega", "deploy", "construye", "build", "construir",
            "lista", "listar", "ls", "dir", "directorio",

            # Search and analysis
            "busca", "buscar", "search", "find", "encuentra", "localiza",
            "analiza", "analyze", "revisa", "review", "examina", "examine",

            # Development tasks
            "implementa", "implementar", "desarrolla", "develop", "programa", "program",
            "genera", "generate", "haz", "make", "arregla", "fix", "repara", "repair",
            "optimiza", "optimize", "mejora", "improve", "refactoriza", "refactor",
            "testea", "test", "prueba", "debugea", "debug",

            # Database operations
            "consulta", "query", "inserta", "actualiza", "update", "borra", "delete",

            # Git operations
            "commit", "push", "pull", "merge", "branch", "clone",
        ]

        # Code indicators (suggest actionable intent)
        self.code_indicators = [
            # Programming constructs
            "def ", "class ", "function ", "import ", "from ", "const ", "let ", "var ",
            "function(", "=>", "async ", "await ", "try:", "except:", "catch",
            # File extensions
            ".py", ".js", ".ts", ".html", ".css", ".json", ".yml", ".yaml",
            ".md", ".txt", ".sh", ".bash", ".sql",
            # Paths and references
            "./", "../", "src/", "dist/", "node_modules/", "venv/",
            # Package/dependency references
            "package.json", "requirements.txt", "setup.py", "pip install",
            "npm install", "yarn add", "composer", "cargo",
        ]

        # Technical terms that suggest actionable context
        self.technical_terms = [
            # Web/API
            "api", "endpoint", "server", "servidor", "puerto", "port", "host", "url", "link",
            "http", "request", "response", "json", "xml", "rest", "graphql",

            # Database
            "database", "db", "sql", "query", "table", "schema", "migration", "model",
            "sqlite", "postgres", "postgresql", "mysql", "mongodb", "redis",
            "connection", "connect", "insert", "update", "delete", "select", "join",

            # Development
            "framework", "libreria", "library", "dependencia", "dependency", "package",
            "test", "testing", "debug", "error", "exception", "bug", "issue", "fix",
            "build", "compile", "deploy", "deployment", "production", "staging",

            # Git
            "git", "commit", "push", "pull", "clone", "branch", "merge", "rebase",
            "stash", "cherry-pick", "conflict", "status", "log", "diff", "remote",
            "origin", "master", "main", "tag", "release",

            # Containers/DevOps
            "docker", "podman", "container", "contenedor", "image", "imagen",
            "kubernetes", "k8s", "helm", "terraform", "ansible", "ci/cd", "pipeline",
            "aws", "gcp", "azure", "cloud", "serverless", "lambda", "ec2",

            # Package Management
            "npm", "yarn", "pip", "pip3", "composer", "cargo", "go mod",
            "install", "update", "upgrade", "requirements", "package.json",
            "venv", "virtualenv", "conda", "poetry", "pipenv",
        ]

    def classify(self, message: str) -> IntentType:
        """Classify the intent of a user message.

        Args:
            message: The user's message to classify

        Returns:
            IntentType enum value
        """
        self.classification_count += 1

        # Clean and normalize message
        message = self._clean_message(message)

        # Check cache first
        if message in self.cache:
            return self.cache[message]

        # Step 1: Check conversational patterns (highest priority)
        if self._is_conversational(message):
            result = IntentType.CONVERSATIONAL
            self.cache[message] = result
            return result

        # Step 2: Check informational patterns
        if self._is_informational(message):
            result = IntentType.INFORMATIONAL
            self.cache[message] = result
            return result

        # Step 3: Check actionable patterns
        if self._is_actionable(message):
            result = IntentType.ACTIONABLE
            self.cache[message] = result
            return result

        # Step 4: Check analytical patterns (may need tools)
        if self._is_analytical(message):
            result = IntentType.ANALYTICAL
            self.cache[message] = result
            return result

        # Default: unknown (will be handled conservatively)
        result = IntentType.UNKNOWN
        self.cache[message] = result
        return result

    def should_use_tools(self, message: str) -> Tuple[bool, float]:
        """Determine if tools should be used for this message.

        Enhanced logic that considers:
        - Intent classification
        - Technical keywords presence
        - Specific command patterns
        - Project context requirements

        Returns:
            Tuple of (should_use_tools, confidence_score)
        """
        intent = self.classify(message)
        message_lower = message.lower()

        # Conversational never need tools
        if intent == IntentType.CONVERSATIONAL:
            return False, 0.95

        # Informational: distinguish between system questions and general knowledge
        if intent == IntentType.INFORMATIONAL:
            # System questions (about capabilities, help) don't need tools
            if self._is_system_question(message):
                return False, 0.95
            # General knowledge questions should go to API
            else:
                return False, 0.90  # But will be handled by API, not tools

        # Actionable always needs tools
        if intent == IntentType.ACTIONABLE:
            # Check for specialized tool commands that need higher confidence
            specialized_commands = [
                # Git commands
                "commit", "push", "pull", "branch", "merge", "status", "log", "diff",
                # Database commands
                "query", "select", "insert", "update", "delete", "schema", "migration",
                # Package commands
                "install", "update", "npm", "pip", "yarn", "composer",
                # File operations
                "read", "write", "edit", "create", "delete",
            ]

            has_specialized = any(cmd in message_lower for cmd in specialized_commands)
            confidence = 0.95 if has_specialized else 0.90
            return True, confidence

        # Analytical may need tools depending on complexity
        if intent == IntentType.ANALYTICAL:
            complexity = self._calculate_complexity(message)
            technical_score = self._calculate_technical_score(message)

            # Analytical + technical content = likely needs tools
            needs_tools = (complexity > 0.5) or (technical_score > 0.3)
            confidence = 0.75 + (complexity * 0.15) + (technical_score * 0.1)
            return needs_tools, min(confidence, 0.95)

        # Unknown: check for technical content that might need tools
        technical_score = self._calculate_technical_score(message)
        if technical_score > 0.4:  # High technical content
            return True, 0.80

        # Very low technical content + unknown intent = probably conversational
        return False, 0.60

    def _clean_message(self, message: str) -> str:
        """Clean and normalize message for processing."""
        if not message:
            return ""

        # Convert to lowercase and strip
        message = message.lower().strip()

        # Remove extra whitespace
        message = re.sub(r'\s+', ' ', message)

        # Remove punctuation at start/end but keep internal punctuation
        message = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', message)

        return message

    def _is_conversational(self, message: str) -> bool:
        """Check if message is purely conversational."""
        # Check regex patterns
        for pattern in self.conversational_patterns:
            if pattern.match(message):
                return True

        # Check for very short messages (likely conversational)
        if len(message.split()) <= 3:
            # Exclude messages with technical terms or action words
            # FIXED: Check ALL terms, not just the first 10
            has_technical = any(term in message for term in self.technical_terms)
            has_action = any(verb in message for verb in self.actionable_verbs)
            if not has_technical and not has_action:
                return True

        return False

    def _is_informational(self, message: str) -> bool:
        """Check if message is asking for information."""
        # Check for informational keywords (system questions)
        if any(keyword in message for keyword in self.informational_keywords):
            return True

        # Check for general question words (more flexible)
        question_starters = [
            r'\bqué\b', r'\bquien\b', r'\bquién\b', r'\bquienes\b', r'\bquiénes\b',  # what, who
            r'\bcuándo\b', r'\bdónde\b', r'\bcómo\b', r'\bpor\s+qué\b', r'\bpor\s+que\b',  # when, where, how, why
            r'\bcuál\b', r'\bcuales\b', r'\bcuáles\b',  # which
        ]

        for pattern in question_starters:
            if re.search(pattern, message, re.IGNORECASE):
                return True

        # Check for question marks (general questions)
        if '?' in message:
            return True

        return False

    def _is_system_question(self, message: str) -> bool:
        """Check if this is a question about the system/capabilities."""
        message_lower = message.lower()

        # Keywords that indicate questions about the system
        system_keywords = [
            "puedes", "eres", "haces", "funciones", "capacidades",
            "herramientas", "tools", "ayuda", "help", "manual",
            "guía", "guide", "cómo funcionas", "como funcionas",
            "what can you do", "qué puedes hacer"
        ]

        return any(keyword in message_lower for keyword in system_keywords)

    def _is_actionable(self, message: str) -> bool:
        """Check if message is requesting an action that needs tools."""
        # Check for actionable verbs
        if any(verb in message for verb in self.actionable_verbs):
            return True

        # Check for code/file indicators
        if any(indicator in message for indicator in self.code_indicators):
            return True

        # Check for file paths (contains / or \)
        if "/" in message or "\\" in message:
            return True

        # Check for technical terms in actionable context
        has_technical = any(term in message for term in self.technical_terms)
        has_action_indicators = (
            "?" not in message or  # Not a question, likely a command
            any(word in message for word in ["por favor", "please", "necesito", "quiero"])
        )

        if has_technical and has_action_indicators:
            return True

        return False

    def _is_analytical(self, message: str) -> bool:
        """Check if message is analytical (may need tools for complex analysis)."""
        analytical_keywords = [
            "analiza", "analyze", "revisa", "review", "examina", "examine",
            "estudia", "study", "evalúa", "evaluate", "comprueba", "check",
            "verifica", "verify", "valida", "validate", "mide", "measure",
        ]

        # Check for analytical keywords
        if any(keyword in message for keyword in analytical_keywords):
            return True

        # Questions about "how" or "why" might be analytical
        analytical_questions = [
            r'cómo\s+se\s+', r'por\s+qué', r'why\s+', r'how\s+does',
            r'qué\s+pasa\s+si', r'what\s+if', r'cómo\s+funciona',
        ]

        for pattern in analytical_questions:
            if re.search(pattern, message, re.IGNORECASE):
                return True

        return False

    def _calculate_complexity(self, message: str) -> float:
        """Calculate message complexity score (0.0 to 1.0)."""
        score = 0.0

        # Length factor
        word_count = len(message.split())
        if word_count > 20:
            score += 0.3
        elif word_count > 10:
            score += 0.2
        elif word_count > 5:
            score += 0.1

        # Technical terms factor
        technical_count = sum(1 for term in self.technical_terms if term in message)
        score += min(technical_count * 0.1, 0.3)

        # Code indicators factor
        code_count = sum(1 for indicator in self.code_indicators if indicator in message)
        score += min(code_count * 0.1, 0.2)

        # Question complexity
        if "?" in message:
            # Multiple questions = more complex
            question_count = message.count("?")
            score += min(question_count * 0.1, 0.2)

        return min(score, 1.0)

    def _calculate_technical_score(self, message: str) -> float:
        """Calculate technical content score (0.0 to 1.0).

        Higher scores indicate messages that likely need specialized tools.
        """
        score = 0.0
        message_lower = message.lower()

        # Count specialized technical terms by category
        git_terms = ["git", "commit", "push", "pull", "branch", "merge", "clone", "status", "log", "diff"]
        db_terms = ["database", "sql", "query", "table", "schema", "migration", "sqlite", "postgres", "mysql"]
        package_terms = ["npm", "yarn", "pip", "install", "package", "dependency", "requirements"]

        git_count = sum(1 for term in git_terms if term in message_lower)
        db_count = sum(1 for term in db_terms if term in message_lower)
        package_count = sum(1 for term in package_terms if term in message_lower)

        # Specialized tool indicators (high weight)
        if git_count > 0:
            score += min(git_count * 0.3, 0.5)
        if db_count > 0:
            score += min(db_count * 0.3, 0.5)
        if package_count > 0:
            score += min(package_count * 0.3, 0.5)

        # General technical terms (lower weight)
        general_tech_count = sum(1 for term in self.technical_terms if term in message_lower)
        score += min(general_tech_count * 0.05, 0.2)

        # Code/file patterns (medium weight)
        code_patterns = sum(1 for indicator in self.code_indicators if indicator in message_lower)
        score += min(code_patterns * 0.1, 0.2)

        # File paths (strong indicator)
        if "/" in message or "\\" in message:
            score += 0.2

        return min(score, 1.0)

    def get_stats(self) -> Dict[str, any]:
        """Get classification statistics."""
        return {
            "total_classifications": self.classification_count,
            "cache_size": len(self.cache),
            "spacy_available": self.nlp is not None,
            "model_name": self.model_name if self.nlp else None,
        }

    def clear_cache(self):
        """Clear the classification cache."""
        self.cache.clear()

    def __repr__(self) -> str:
        return f"IntentClassifier(model='{self.model_name}', spacy={self.nlp is not None})"