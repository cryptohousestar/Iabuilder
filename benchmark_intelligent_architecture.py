#!/usr/bin/env python3
"""
Benchmark script for the Intelligent Architecture.

This script measures:
- Classification accuracy of IntentClassifier
- Response time improvements
- Tool usage reduction
- Overall system performance

Run with: python benchmark_intelligent_architecture.py
"""

import time
import sys
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from iabuilder.intent_classifier import IntentClassifier, IntentType


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


class IntelligentArchitectureBenchmark:
    """Benchmark suite for the intelligent architecture."""

    def __init__(self):
        """Initialize benchmark with test data."""
        self.classifier = IntentClassifier()
        self.test_cases = self._create_test_cases()

    def _create_test_cases(self) -> List[Tuple[str, IntentType, bool]]:
        """Create comprehensive test cases for benchmarking.

        Returns:
            List of (message, expected_intent, should_use_tools) tuples
        """
        return [
            # CONVERSATIONAL - No tools
            ("hola", IntentType.CONVERSATIONAL, False),
            ("hello", IntentType.CONVERSATIONAL, False),
            ("buenos días", IntentType.CONVERSATIONAL, False),
            ("buenas tardes", IntentType.CONVERSATIONAL, False),
            ("buenas noches", IntentType.CONVERSATIONAL, False),
            ("¿cómo estás?", IntentType.CONVERSATIONAL, False),
            ("how are you", IntentType.CONVERSATIONAL, False),
            ("¿qué tal?", IntentType.CONVERSATIONAL, False),
            ("gracias", IntentType.CONVERSATIONAL, False),
            ("thanks", IntentType.CONVERSATIONAL, False),
            ("thank you", IntentType.CONVERSATIONAL, False),
            ("adiós", IntentType.CONVERSATIONAL, False),
            ("bye", IntentType.CONVERSATIONAL, False),
            ("hasta luego", IntentType.CONVERSATIONAL, False),
            ("ok", IntentType.CONVERSATIONAL, False),
            ("vale", IntentType.CONVERSATIONAL, False),
            ("entendido", IntentType.CONVERSATIONAL, False),

            # INFORMATIONAL - No tools
            ("qué puedes hacer", IntentType.INFORMATIONAL, False),
            ("what can you do", IntentType.INFORMATIONAL, False),
            ("qué herramientas tienes", IntentType.INFORMATIONAL, False),
            ("what tools do you have", IntentType.INFORMATIONAL, False),
            ("cómo funcionas", IntentType.INFORMATIONAL, False),
            ("how do you work", IntentType.INFORMATIONAL, False),
            ("explícame cómo usar esto", IntentType.INFORMATIONAL, False),
            ("explain how to use this", IntentType.INFORMATIONAL, False),
            ("qué es esto", IntentType.INFORMATIONAL, False),
            ("what is this", IntentType.INFORMATIONAL, False),
            ("help", IntentType.INFORMATIONAL, False),
            ("ayuda", IntentType.INFORMATIONAL, False),

            # ACTIONABLE - Tools needed
            ("lee el archivo config.json", IntentType.ACTIONABLE, True),
            ("read the config.py file", IntentType.ACTIONABLE, True),
            ("crea un archivo llamado test.py", IntentType.ACTIONABLE, True),
            ("create a new file called hello.py", IntentType.ACTIONABLE, True),
            ("edita el código", IntentType.ACTIONABLE, True),
            ("edit the code", IntentType.ACTIONABLE, True),
            ("borra ese archivo", IntentType.ACTIONABLE, True),
            ("delete that file", IntentType.ACTIONABLE, True),
            ("ejecuta el comando ls", IntentType.ACTIONABLE, True),
            ("run the ls command", IntentType.ACTIONABLE, True),
            ("instala las dependencias", IntentType.ACTIONABLE, True),
            ("install dependencies", IntentType.ACTIONABLE, True),
            ("compila el proyecto", IntentType.ACTIONABLE, True),
            ("compile the project", IntentType.ACTIONABLE, True),
            ("despliega la aplicación", IntentType.ACTIONABLE, True),
            ("deploy the application", IntentType.ACTIONABLE, True),

            # CODE CONTENT - Tools needed
            ("crea una función de fibonacci", IntentType.ACTIONABLE, True),
            ("write a fibonacci function", IntentType.ACTIONABLE, True),
            ("implementa una clase", IntentType.ACTIONABLE, True),
            ("implement a class", IntentType.ACTIONABLE, True),
            ("def suma(a, b): return a + b", IntentType.ACTIONABLE, True),
            ("function add(a, b) { return a + b; }", IntentType.ACTIONABLE, True),
            ("class Calculator:", IntentType.ACTIONABLE, True),
            ("import os", IntentType.ACTIONABLE, True),

            # ANALYTICAL - May need tools depending on complexity
            ("analiza este código", IntentType.ANALYTICAL, False),  # Simple analysis
            ("analyze this code", IntentType.ANALYTICAL, False),
            ("revisa la implementación", IntentType.ANALYTICAL, False),
            ("review the implementation", IntentType.ANALYTICAL, False),
            ("evalúa el rendimiento", IntentType.ANALYTICAL, True),  # May need tools
            ("evaluate performance", IntentType.ANALYTICAL, True),

            # EDGE CASES
            ("", IntentType.UNKNOWN, False),  # Empty message
            ("?", IntentType.UNKNOWN, False),  # Just punctuation
            ("hola mundo", IntentType.CONVERSATIONAL, False),  # Mixed intent
            ("lee el archivo y dime qué hace", IntentType.ACTIONABLE, True),  # Combined
        ]

    def run_benchmark(self) -> BenchmarkStats:
        """Run complete benchmark suite.

        Returns:
            BenchmarkStats with comprehensive results
        """
        print("🚀 INICIANDO BENCHMARK - ARQUITECTURA INTELIGENTE")
        print("=" * 60)

        results = []
        start_time = time.time()

        for i, (message, expected_intent, expected_tools) in enumerate(self.test_cases, 1):
            print(f"🔍 Test {i:2d}/{len(self.test_cases):2d}: {message[:50]:50}", end="")

            # Time the classification
            test_start = time.time()

            predicted_intent = self.classifier.classify(message)
            should_use_tools, confidence = self.classifier.should_use_tools(message)

            test_time = time.time() - test_start

            # Check correctness
            intent_correct = predicted_intent == expected_intent
            tools_correct = should_use_tools == expected_tools

            # Overall correctness (both must be correct)
            correct = intent_correct and tools_correct

            # Create result
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

            # Show result
            status = "✅" if correct else "❌"
            print(f" {status} ({test_time:.3f}s)")

        total_time = time.time() - start_time

        # Calculate statistics
        stats = self._calculate_stats(results, total_time)

        # Print detailed results
        self._print_results(results, stats)

        return stats

    def _calculate_stats(self, results: List[BenchmarkResult], total_time: float) -> BenchmarkStats:
        """Calculate comprehensive statistics from results."""
        total_tests = len(results)
        correct_classifications = sum(1 for r in results if r.correct)
        correct_tool_decisions = sum(1 for r in results if r.should_use_tools_predicted == r.should_use_tools_expected)

        total_response_time = sum(r.response_time for r in results)
        average_response_time = total_response_time / total_tests

        accuracy_percentage = (correct_classifications / total_tests) * 100
        tool_decision_accuracy = (correct_tool_decisions / total_tests) * 100

        return BenchmarkStats(
            total_tests=total_tests,
            correct_classifications=correct_classifications,
            correct_tool_decisions=correct_tool_decisions,
            average_response_time=average_response_time,
            accuracy_percentage=accuracy_percentage,
            tool_decision_accuracy=tool_decision_accuracy,
            total_time=total_time
        )

    def _print_results(self, results: List[BenchmarkResult], stats: BenchmarkStats):
        """Print comprehensive benchmark results."""
        print("\n" + "=" * 60)
        print("📊 RESULTADOS DEL BENCHMARK")
        print("=" * 60)

        print(f"🎯 Tests Totales: {stats.total_tests}")
        print(f"✅ Clasificaciones Correctas: {stats.correct_classifications}")
        print(f"📈 Precisión General: {stats.accuracy_percentage:.1f}%")
        print(f"🔧 Precisión Decisiones Tools: {stats.tool_decision_accuracy:.1f}%")
        print(f"⚡ Tiempo Promedio Respuesta: {stats.average_response_time:.3f}s")
        print(f"⏱️  Tiempo Total Benchmark: {stats.total_time:.2f}s")

        # Classifier stats
        classifier_stats = self.classifier.get_stats()
        print(f"\n🤖 Stats del Classifier:")
        print(f"   - Clasificaciones realizadas: {classifier_stats['total_classifications']}")
        print(f"   - Tamaño del cache: {classifier_stats['cache_size']}")
        print(f"   - spaCy disponible: {'✅' if classifier_stats['spacy_available'] else '❌'}")

        # Show failures if any
        failures = [r for r in results if not r.correct]
        if failures:
            print(f"\n❌ FALLOS ENCONTRADOS ({len(failures)}):")
            print("-" * 40)
            for failure in failures[:10]:  # Show first 10 failures
                print(f"   📝 '{failure.message}'")
                print(f"      Esperado: {failure.expected_intent.value} → Tools: {failure.should_use_tools_expected}")
                print(f"      Obtenido: {failure.predicted_intent.value} → Tools: {failure.should_use_tools_predicted}")
                print(f"      Confianza: {failure.confidence:.2f}")
                print()

        # Performance analysis
        self._analyze_performance(results, stats)

    def _analyze_performance(self, results: List[BenchmarkResult], stats: BenchmarkStats):
        """Analyze performance characteristics."""
        print("\n🔬 ANÁLISIS DE PERFORMANCE")
        print("-" * 40)

        # Response time distribution
        times = [r.response_time for r in results]
        fast_responses = sum(1 for t in times if t < 0.01)  # < 10ms
        medium_responses = sum(1 for t in times if 0.01 <= t < 0.1)  # 10-100ms
        slow_responses = sum(1 for t in times if t >= 0.1)  # > 100ms

        print(f"⚡ Respuestas rápidas (<10ms): {fast_responses} ({fast_responses/len(times)*100:.1f}%)")
        print(f"🟡 Respuestas medias (10-100ms): {medium_responses} ({medium_responses/len(times)*100:.1f}%)")
        print(f"🐌 Respuestas lentas (>100ms): {slow_responses} ({slow_responses/len(times)*100:.1f}%)")

        # Intent distribution
        intents = {}
        for result in results:
            intent_name = result.predicted_intent.value
            intents[intent_name] = intents.get(intent_name, 0) + 1

        print("\n🎭 Distribución de Intenciones:")
        for intent, count in sorted(intents.items()):
            percentage = (count / len(results)) * 100
            print(".1f")
        # Tool usage reduction
        tool_usage = sum(1 for r in results if r.should_use_tools_predicted)
        tool_reduction = ((len(results) - tool_usage) / len(results)) * 100

        print("\n🛠️  Análisis de Uso de Tools:")
        print(f"   - Mensajes que requieren tools: {tool_usage}/{len(results)} ({tool_usage/len(results)*100:.1f}%)")
        print(".1f")
        # Expected improvements
        print("\n🎯 Mejoras Esperadas:")
        print("   - 90% menos llamadas innecesarias a tools")
        print("   - 95% accuracy en clasificación de intenciones")
        print("   - Respuestas instantáneas para conversaciones")
        print("   - Mejor experiencia de usuario")
        # Success criteria
        success_criteria = [
            ("Accuracy > 90%", stats.accuracy_percentage >= 90),
            ("Tool decisions > 85%", stats.tool_decision_accuracy >= 85),
            ("Avg response < 50ms", stats.average_response_time < 0.05),
            ("spaCy funcionando", self.classifier.get_stats()['spacy_available']),
        ]

        print("\n✅ Criterios de Éxito:")
        for criterion, met in success_criteria:
            status = "✅" if met else "❌"
            print(f"   {status} {criterion}")

        all_met = all(met for _, met in success_criteria)
        overall_status = "🎉 ÉXITO COMPLETO" if all_met else "⚠️  REQUIERE MEJORAS"
        print(f"\n🏆 STATUS GENERAL: {overall_status}")

        if all_met:
            print("\n🚀 ¡La Arquitectura Inteligente está lista para producción!")
            print("   - Precisión excelente")
            print("   - Performance óptima")
            print("   - Reducción significativa de tool calls innecesarios")
        else:
            print("\n🔧 Áreas de mejora identificadas:")
            if stats.accuracy_percentage < 90:
                print("   - Mejorar precisión de clasificación")
            if stats.tool_decision_accuracy < 85:
                print("   - Refinar lógica de decisión de tools")
            if stats.average_response_time >= 0.05:
                print("   - Optimizar velocidad de respuesta")
            if not self.classifier.get_stats()['spacy_available']:
                print("   - Resolver problemas con spaCy")


def main():
    """Main benchmark execution."""
    print("🤖 BENCHMARK - ARQUITECTURA INTELIGENTE GROQ CLI")
    print("Evaluando precisión, performance y eficiencia de la nueva arquitectura\n")

    # Check if spaCy is available
    try:
        from iabuilder.intent_classifier import SPACY_AVAILABLE
        if not SPACY_AVAILABLE:
            print("⚠️  ADVERTENCIA: spaCy no está disponible. Usando clasificación básica.")
            print("   Para mejores resultados, instala spaCy y el modelo español.")
            print("   Ejecuta: pip install spacy && python -m spacy download es_core_news_sm\n")
    except ImportError:
        print("❌ ERROR: No se puede importar IntentClassifier")
        return 1

    # Run benchmark
    benchmark = IntelligentArchitectureBenchmark()
    stats = benchmark.run_benchmark()

    # Return exit code based on success
    if stats.accuracy_percentage >= 90:
        print("\n🎉 Benchmark completado exitosamente!")
        return 0
    else:
        print(f"\n⚠️  Benchmark completado con precisión {stats.accuracy_percentage:.1f}% (< 90%)")
        return 1


if __name__ == "__main__":
    exit(main())