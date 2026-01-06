#!/usr/bin/env python3
"""
Análisis de diferencias entre modelos de Groq (Llama) vs OpenAI (GPT)
en la interpretación de system prompts y function calling.
"""

def analyze_model_differences():
    """Analizar diferencias clave entre modelos de Groq y OpenAI."""

    print("🧠 ANÁLISIS: Groq (Llama) vs OpenAI (GPT) - Diferencias en System Prompts")
    print("=" * 80)

    differences = {
        "Arquitectura Base": {
            "OpenAI (GPT)": "Transformer decoder-only, entrenado con instrucciones específicas",
            "Groq (Llama)": "Transformer decoder-only, pero arquitectura más abierta/conversacional",
            "Implicación": "Llama puede ser más flexible pero menos 'obediente' a reglas estrictas"
        },

        "Estilo de Fine-tuning": {
            "OpenAI (GPT)": "Fine-tuning extensivo para seguir instrucciones precisas",
            "Groq (Llama)": "Fine-tuning más conservador, mantiene naturaleza conversacional",
            "Implicación": "GPT responde mejor a prompts estructurados con reglas claras"
        },

        "Interpretación de System Prompts": {
            "OpenAI (GPT)": "Trata system prompt como 'instrucciones estrictas a seguir'",
            "Groq (Llama)": "Trata system prompt como 'contexto conversacional'",
            "Implicación": "Llama puede ignorar o reinterpretar reglas muy estrictas"
        },

        "Function Calling": {
            "OpenAI (GPT)": "Function calling nativo en el modelo",
            "Groq (Llama)": "Function calling implementado via API compatibility",
            "Implicación": "Groq puede necesitar diferentes cues para activar tools"
        },

        "Longitud de Prompt": {
            "OpenAI (GPT)": "Maneja bien prompts largos con estructura clara",
            "Groq (Llama)": "Prefiere prompts más concisos y directos",
            "Implicación": "Prompts largos pueden confundir a Llama models"
        },

        "Estilo de Instrucción": {
            "OpenAI (GPT)": "Responde bien a: 'DEBES hacer X', 'SIEMPRE usa Y'",
            "Groq (Llama)": "Responde mejor a: 'Puedes usar X para...', 'Cuando necesites Y...'"
            "Implicación": "El lenguaje imperativo puede ser contraproducente con Llama"
        }
    }

    for category, details in differences.items():
        print(f"\n🔍 {category}:")
        print(f"   OpenAI: {details['OpenAI (GPT)']}")
        print(f"   Groq: {details['Groq (Llama)']}")
        print(f"   💡 Implicación: {details['Implicación']}")

    print("\n" + "=" * 80)
    print("🎯 HIPÓTESIS: El System Prompt Actual Puede Ser Problemático")
    print("=" * 80)

    current_prompt_issues = [
        "❌ MUY LARGO (125+ líneas) - Llama prefiere conciso",
        "❌ Lenguaje IMPERATIVO ('MUST', 'STRICT', 'MANDATORY') - Llama más flexible",
        "❌ Reglas DEMASIADO ESTRICTAS - Llama puede 'rebelarse' contra restricciones",
        "❌ Enfoque en 'prohibiciones' - Llama responde mejor a sugerencias positivas",
        "❌ Estructura compleja con secciones - Llama mejor con flujo natural",
        "❌ Asume comportamiento 'obediente' como GPT - Llama más conversacional"
    ]

    for issue in current_prompt_issues:
        print(f"   {issue}")

    print("\n💡 SOLUCIÓN PROPUESTA:")
    print("   Crear prompt optimizado para Llama models:")
    print("   - Más corto y conversacional")
    print("   - Lenguaje sugerente, no imperativo")
    print("   - Enfoque en capacidades, no restricciones")
    print("   - Ejemplos naturales, no reglas estrictas")

def compare_prompt_styles():
    """Comparar estilos de prompt para diferentes modelos."""

    print("\n" + "=" * 80)
    print("📝 COMPARACIÓN: Estilos de Prompt Optimizados")
    print("=" * 80)

    # Prompt estilo OpenAI (actual)
    openai_style = """# 🤖 AI Development Assistant - STRICT TOOL USAGE REQUIRED

You are a development assistant with access to tools. You MUST use tools for ALL development actions.

## 🚨 CRITICAL: ALWAYS USE TOOLS FOR:
### 📁 FILE OPERATIONS (MANDATORY)
- **Creating files** → `write_file`
- **Reading files** → `read_file`

## 🚫 ONLY USE PLAIN TEXT FOR:
- Greetings ("hola", "hello")
- Questions about your capabilities

## ⚠️ CRITICAL RULE:
**NEVER simulate actions with text. ALWAYS use tools for development tasks.**
**If you need to create/edit/read files: USE TOOLS IMMEDIATELY.**"""

    # Prompt estilo Groq/Llama optimizado
    llama_style = """# 🤖 AI Assistant for Development

I'm a helpful AI with access to development tools. I can help you with coding tasks using these tools:

📁 Files: read_file, write_file, edit_file
💻 System: execute_bash, run_python
🔍 Search: grep_search, glob_search

When you need to work with files or run commands, I'll automatically use the right tool.

For example:
- To read a file: I'll use read_file
- To run a command: I'll use execute_bash

What would you like to work on?"""

    print("\n📋 ESTILO ACTUAL (Optimizado para OpenAI/GPT):")
    print("-" * 50)
    for line in openai_style.split('\n')[:10]:
        print(f"   {line}")
    print("   ... (continúa con reglas estrictas)")

    print("\n🎯 ESTILO PROPUESTO (Optimizado para Groq/Llama):")
    print("-" * 50)
    for line in llama_style.split('\n'):
        print(f"   {line}")

    print("\n🔄 DIFERENCIAS CLAVE:")
    print("   OpenAI style: Reglas estrictas, imperativo, restricciones")
    print("   Llama style: Conversacional, sugerente, capacidades")
    print("   OpenAI style: 'DEBE usar tools SIEMPRE'")
    print("   Llama style: 'Puedo usar tools cuando ayude'")

if __name__ == "__main__":
    analyze_model_differences()
    compare_prompt_styles()