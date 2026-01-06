#!/usr/bin/env python3
"""Test script para verificar el flujo completo de Gemini."""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from iabuilder.tools import setup_tools, get_tool_registry
from iabuilder.ai.response_processor import ResponseProcessor
from iabuilder.conversation import Conversation
from iabuilder.renderer import Renderer

def test_tool_code_parsing():
    """Test parsing de bloques tool_code con comandos directos."""
    print("=" * 60)
    print("TEST 1: Parsing de tool_code con comando directo")
    print("=" * 60)

    # Setup
    setup_tools()
    conv = Conversation()
    rp = ResponseProcessor(conv, Renderer())

    # Simular respuesta de Gemini con tool_code
    test_content = '''Voy a listar los archivos:

```tool_code
ls -la /home/linuxpc/Desktop
```

Esto te mostrará todos los archivos.'''

    # Parsear bloques
    calls = rp._parse_tool_code_blocks(test_content)

    print(f"\nContenido parseado: {len(calls)} llamadas")
    for c in calls:
        print(f"  - {c.function.name}({c.function.arguments})")

    if len(calls) == 0:
        print("❌ FALLÓ: No se detectaron llamadas")
        return False

    if calls[0].function.name != "execute_bash":
        print(f"❌ FALLÓ: Se esperaba 'execute_bash', se obtuvo '{calls[0].function.name}'")
        return False

    print("✅ PASÓ: Se detectó correctamente execute_bash")
    return True


def test_tool_execution():
    """Test ejecución de herramientas."""
    print("\n" + "=" * 60)
    print("TEST 2: Ejecución de herramientas")
    print("=" * 60)

    # Setup
    setup_tools()
    registry = get_tool_registry()

    # Listar herramientas disponibles
    tools = registry.list_tools()
    print(f"\nHerramientas disponibles: {tools}")

    if 'execute_bash' not in tools:
        print("❌ FALLÓ: execute_bash no está en el registry")
        return False

    # Intentar ejecutar
    print("\nEjecutando: execute_bash(command='echo test')")
    result = registry.execute('execute_bash', command='echo test')

    if not result.get('success'):
        print(f"❌ FALLÓ: {result.get('error')}")
        return False

    print(f"✅ PASÓ: {result.get('summary', 'Ejecutado correctamente')}")
    return True


def test_response_processing():
    """Test procesamiento completo de respuesta con tool_code."""
    print("\n" + "=" * 60)
    print("TEST 3: Procesamiento completo de respuesta")
    print("=" * 60)

    # Setup
    setup_tools()
    conv = Conversation()
    conv.add_message("user", "lista los archivos del directorio actual")

    rp = ResponseProcessor(conv, Renderer())

    # Simular respuesta de Gemini
    class MockResponse:
        def __init__(self, content):
            self.choices = [type('obj', (object,), {
                'message': type('obj', (object,), {
                    'content': content,
                    'tool_calls': None
                })()
            })()]

    gemini_response = '''Voy a listar los archivos:

```tool_code
ls -la
```'''

    response = MockResponse(gemini_response)

    print(f"\nProcesando respuesta de Gemini...")
    print(f"Contenido: {gemini_response[:100]}...")

    try:
        result = rp._process_legacy(response, tools=get_tool_registry().get_schemas())

        if result == rp.NEEDS_FOLLOWUP:
            print("✅ PASÓ: Se detectó necesidad de follow-up (herramienta ejecutada)")
            return True
        else:
            print(f"❌ FALLÓ: Resultado inesperado: {result}")
            return False

    except Exception as e:
        print(f"❌ FALLÓ con excepción: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecutar todos los tests."""
    print("\n🧪 TESTING IABUILDER - FLUJO GEMINI\n")

    results = []

    # Test 1: Parsing
    results.append(("Parsing tool_code", test_tool_code_parsing()))

    # Test 2: Ejecución
    results.append(("Ejecución de herramientas", test_tool_execution()))

    # Test 3: Procesamiento completo
    results.append(("Procesamiento completo", test_response_processing()))

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{status}: {name}")

    total_passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {total_passed}/{len(results)} tests pasados")

    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
