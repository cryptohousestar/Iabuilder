#!/usr/bin/env python3
"""Test script for intent classification."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

try:
    from iabuilder.intent_classifier import IntentClassifier, IntentType

    def test_classification():
        classifier = IntentClassifier()

        test_cases = [
            ("que modelo sos", "sistema"),
            ("quien invento la electricidad", "conocimiento general"),
            ("hola", "conversacional"),
            ("crea un archivo", "accionable"),
            ("que puedes hacer", "sistema"),
            ("como estas", "conversacional"),
        ]

        print("🧪 Probando clasificación de intenciones:\n")

        for message, expected_type in test_cases:
            intent = classifier.classify(message)
            should_use_tools, confidence = classifier.should_use_tools(message)
            is_system = classifier._is_system_question(message)

            print(f"📝 \"{message}\"")
            print(f"   Intent: {intent.value} (conf: {confidence:.2f})")
            print(f"   Usa tools: {should_use_tools}")
            print(f"   Es pregunta sistema: {is_system}")
            print(f"   Tipo esperado: {expected_type}")
            print()

    if __name__ == "__main__":
        test_classification()

except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Esto puede ser porque faltan dependencias o el entorno virtual no está configurado.")