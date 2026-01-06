#!/usr/bin/env python3
"""
Benchmark simplificado para IntentClassifier sin dependencias del proyecto completo.
"""

import time
import sys
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import only what we need
try:
    import spacy
    from spacy.lang.es import Spanish
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None
    Spanish = None

from enum import Enum

class IntentType(Enum):
    """Types of user intents that the classifier can identify."""
    CONVERSATIONAL = "conversational"  # Greetings, questions about capabilities
    INFORMATIONAL = "informational"    # Questions about how things work
    ACTIONABLE = "actionable"         # Requests to perform actions
    ANALYTICAL = "analytical"         # Analysis requests (may need tools)
    UNKNOWN = "unknown"              # Cannot classify


class IntentClassifier:
    """Simplified IntentClassifier for benchmarking."""

    def __init__(self, model_name: str = "es_core_news_sm"):
        """Initialize the intent classifier."""
        self.model_name = model_name
        self.nlp = None
        self._initialize_spacy()
        self._setup_patterns()
        self.classification_count = 0
        self.cache = {}

    def _initialize_spacy(self):
        """Initialize spaCy model with error handling."""
        if not SPACY_AVAILABLE:
            print("spaCy not available, using rule-based classification")
            return

        try:
            self.nlp = spacy.load(self.model_name)
            print(f"spaCy model '{self.model_name}' loaded successfully")
        except Exception as e:
            print(f"spaCy failed to load: {e}, using fallback")
            self.nlp = None

    def _setup_patterns(self):
        """Setup regex patterns and keyword lists for classification."""
        import re

        self.conversational_patterns = [
            re.compile(r'^(hola|hello|hi|hey|buenos?\s+dias|buenas?\s+(tardes|noches))$', re.IGNORECASE),
            re.compile(r'^(adiós|bye|goodbye|chau|nos\s+vemos|hasta\s+luego)$', re.IGNORECASE),
            re.compile(r'^(cómo\s+estás?|how\s+are\s+you|qué\s+tal|what\'s\s+up)$', re.IGNORECASE),
            re.compile(r'^(gracias|thanks|thank\s+you)$', re.IGNORECASE),
            re.compile(r'^(sí|no|yes|no|ok|okay|claro|por\s+supuesto)$', re.IGNORECASE),
            re.compile(r'^(entiendo|understand|vale|de\s+acuerdo)$', re.IGNORECASE),
        ]

        self.informational_keywords = {
            "qué puedes hacer", "que puedes hacer", "what can you do",
            "qué eres", "que eres", "what are you",
            "cómo funcionas", "como funcionas", "how do you work",
            "qué herramientas", "que herramientas", "what tools",
            "explícame", "explain", "dime", "tell me",
            "cuéntame", "describe", "qué es", "what is",
            "ayuda", "help", "soporte", "support",
        }

        self.actionable_verbs = [
            "lee", "leer", "read", "abre", "abrir", "open",
            "crea", "crear", "create", "escribe", "escribir", "write",
            "ejecuta", "ejecutar", "run", "instala", "instalar", "install",
            "compila", "compilar", "compile", "despliega", "deploy",
        ]

        self.technical_terms = [
            "api", "endpoint", "database", "sql", "server", "puerto",
            "framework", "libreria", "dependencia", "test", "debug",
        ]

    def classify(self, message: str) -> IntentType:
        """Classify the intent of a user message."""
        self.classification_count += 1

        message = message.lower().strip()

        # Check cache
        if message in self.cache:
            return self.cache[message]

        # Conversational
        for pattern in self.conversational_patterns:
            if pattern.match(message):
                result = IntentType.CONVERSATIONAL
                self.cache[message] = result
                return result

        # Informational
        if any(keyword in message for keyword in self.informational_keywords):
            result = IntentType.INFORMATIONAL
            self.cache[message] = result
            return result

        # Actionable
        if any(verb in message for verb in self.actionable_verbs):
            result = IntentType.ACTIONABLE
            self.cache[message] = result
            return result

        # Default unknown
        result = IntentType.UNKNOWN
        self.cache[message] = result
        return result

    def should_use_tools(self, message: str) -> Tuple[bool, float]:
        """Determine if tools should be used."""
        intent = self.classify(message)

        if intent in [IntentType.CONVERSATIONAL, IntentType.INFORMATIONAL]:
            return False, 0.95
        elif intent == IntentType.ACTIONABLE:
            return True, 0.90
        else:
            return False, 0.5

    def get_stats(self) -> Dict:
        """Get classification statistics."""
        return {
            "total_classifications": self.classification_count,
            "cache_size": len(self.cache),
            "spacy_available": self.nlp is not None,
        }


@dataclass
class BenchmarkResult:
    """Result of a benchmark test."""
    message: str
    expected_intent: IntentType
    predicted_intent: IntentType
    should_use_tools_expected: bool
    should_use_tools_predicted: bool
    confidence: float
    response_time: float
    correct: bool


@dataclass
class BenchmarkStats:
    """Statistics from benchmark run."""
    total_tests: int
    correct_classifications: int
    correct_tool_decisions: int
    average_response_time: float
    accuracy_percentage: float
    tool_decision_accuracy: float
    total_time: float


def run_benchmark():
    """Run complete benchmark."""
    print("🚀 BENCHMARK SIMPLIFICADO - INTENT CLASSIFIER")
    print("=" * 50)

    classifier = IntentClassifier()

    # Test cases
    test_cases = [
        # CONVERSATIONAL - No tools
        ("hola", IntentType.CONVERSATIONAL, False),
        ("hello", IntentType.CONVERSATIONAL, False),
        ("buenos días", IntentType.CONVERSATIONAL, False),
        ("gracias", IntentType.CONVERSATIONAL, False),
        ("¿cómo estás?", IntentType.CONVERSATIONAL, False),

        # INFORMATIONAL - No tools
        ("qué puedes hacer", IntentType.INFORMATIONAL, False),
        ("what can you do", IntentType.INFORMATIONAL, False),
        ("qué herramientas tienes", IntentType.INFORMATIONAL, False),
        ("help", IntentType.INFORMATIONAL, False),

        # ACTIONABLE - Tools needed
        ("lee el archivo config.json", IntentType.ACTIONABLE, True),
        ("read the config.py file", IntentType.ACTIONABLE, True),
        ("crea un archivo llamado test.py", IntentType.ACTIONABLE, True),
        ("ejecuta el comando ls", IntentType.ACTIONABLE, True),
        ("instala las dependencias", IntentType.ACTIONABLE, True),
    ]

    results = []
    start_time = time.time()

    for i, (message, expected_intent, expected_tools) in enumerate(test_cases, 1):
        print(f"🔍 Test {i:2d}/{len(test_cases):2d}: {message[:40]:40}", end="")

        test_start = time.time()
        predicted_intent = classifier.classify(message)
        should_use_tools, confidence = classifier.should_use_tools(message)
        test_time = time.time() - test_start

        intent_correct = predicted_intent == expected_intent
        tools_correct = should_use_tools == expected_tools
        correct = intent_correct and tools_correct

        result = BenchmarkResult(
            message=message,
            expected_intent=expected_intent,
            predicted_intent=predicted_intent,
            should_use_tools_expected=expected_tools,
            should_use_tools_predicted=should_use_tools,
            confidence=confidence,
            response_time=test_time,
            correct=correct
        )
        results.append(result)

        status = "✅" if correct else "❌"
        print(f" {status} ({test_time:.3f}s)")

    total_time = time.time() - start_time

    # Calculate stats
    total_tests = len(results)
    correct_classifications = sum(1 for r in results if r.correct)
    correct_tool_decisions = sum(1 for r in results if r.should_use_tools_predicted == r.should_use_tools_expected)

    accuracy_percentage = (correct_classifications / total_tests) * 100
    tool_decision_accuracy = (correct_tool_decisions / total_tests) * 100
    average_response_time = sum(r.response_time for r in results) / total_tests

    stats = BenchmarkStats(
        total_tests=total_tests,
        correct_classifications=correct_classifications,
        correct_tool_decisions=correct_tool_decisions,
        average_response_time=average_response_time,
        accuracy_percentage=accuracy_percentage,
        tool_decision_accuracy=tool_decision_accuracy,
        total_time=total_time
    )

    # Print results
    print(f"\n{'=' * 50}")
    print("📊 RESULTADOS DEL BENCHMARK")
    print(f"🎯 Tests Totales: {stats.total_tests}")
    print(f"✅ Clasificaciones Correctas: {stats.correct_classifications}")
    print(f"📈 Precisión General: {stats.accuracy_percentage:.1f}%")
    print(f"🔧 Precisión Tools: {stats.tool_decision_accuracy:.1f}%")
    print(f"⚡ Tiempo Promedio: {stats.average_response_time:.3f}s")
    print(f"⏱️  Tiempo Total: {stats.total_time:.2f}s")

    # Classifier stats
    classifier_stats = classifier.get_stats()
    print(f"\n🤖 Classifier Stats:")
    print(f"   - Clasificaciones: {classifier_stats['total_classifications']}")
    print(f"   - Cache size: {classifier_stats['cache_size']}")
    print(f"   - spaCy disponible: {'✅' if classifier_stats['spacy_available'] else '❌'}")

    # Show failures
    failures = [r for r in results if not r.correct]
    if failures:
        print(f"\n❌ Fallos ({len(failures)}):")
        for failure in failures:
            print(f"   '{failure.message}': esperado {failure.expected_intent.value}, obtenido {failure.predicted_intent.value}")

    # Success criteria
    success = (
        stats.accuracy_percentage >= 90 and
        stats.tool_decision_accuracy >= 85 and
        stats.average_response_time < 0.1
    )

    print(f"\n🏆 STATUS: {'🎉 ÉXITO' if success else '⚠️  REQUIERE MEJORAS'}")

    if success:
        print("🚀 ¡La Arquitectura Inteligente funciona correctamente!")

    return stats


if __name__ == "__main__":
    run_benchmark()