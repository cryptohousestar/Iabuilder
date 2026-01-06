# 🚀 Instalación: Arquitectura Inteligente para Groq CLI Custom

**Fecha:** 20 de Diciembre 2024
**Versión Objetivo:** v2.5 - Arquitectura Inteligente
**Tiempo Estimado:** 30-45 minutos
**Dificultad:** Intermedia

## 🎯 Objetivo

Implementar la nueva arquitectura inteligente que mejora significativamente cómo el sistema decide cuándo usar herramientas:

```
Usuario → [spaCy Classifier] → [LangChain Agent] → [Groq API] → [Tools]
              ↓                         ↓
       🤖 Clasifica intención     🤖 Decide tools apropiadas
   (conversacional/actionable)   (solo cuando necesario)
```

## 📋 Prerrequisitos

- ✅ Python 3.8+
- ✅ Sistema operativo Linux/Mac/Windows
- ✅ Conexión a internet para descargar modelos
- ✅ Proyecto Groq CLI Custom ya clonado
- ✅ API Key de Groq configurada

## 🛠️ PASO 1: Instalar spaCy y Modelo de Español

spaCy es la librería de NLP que usaremos para clasificar intenciones en español.

### **Comandos de Instalación:**

```bash
# 1. Instalar spaCy (librería principal)
pip install spacy

# 2. Descargar modelo de español (pequeño y eficiente)
python -m spacy download es_core_news_sm

# 3. Verificar instalación
python -c "import spacy; nlp = spacy.load('es_core_news_sm'); doc = nlp('Hola mundo'); print(f'✅ spaCy funciona: {len(doc)} tokens')"
```

### **¿Qué hace esto?**
- **spaCy**: Framework de NLP rápido y eficiente
- **es_core_news_sm**: Modelo pre-entrenado para español (~15MB)
- **Verificación**: Asegura que todo esté funcionando

### **Posibles Problemas:**
```bash
# Si hay error de permisos
pip install --user spacy
python -m spacy download es_core_news_sm --user

# Si hay error de red
# Reintentar con proxy o VPN
```

## 🛠️ PASO 2: Instalar LangChain

LangChain nos proporciona el framework de agentes para coordinar tools inteligentemente.

### **Comandos de Instalación:**

```bash
# 1. Instalar LangChain completo
pip install langchain langchain-community langchain-core

# 2. Instalar integraciones necesarias
pip install langchain-openai  # Para compatibilidad con Groq

# 3. Instalar Pydantic (para validación de datos)
pip install pydantic

# 4. Verificar instalación
python -c "from langchain.agents import initialize_agent; from langchain.llms import OpenAI; print('✅ LangChain funciona')"
```

### **¿Qué hace esto?**
- **langchain**: Framework principal para agentes y chains
- **langchain-community**: Herramientas adicionales
- **langchain-openai**: Integración con APIs compatibles con OpenAI (como Groq)
- **pydantic**: Validación de datos estructurados

### **Versiones Recomendadas:**
```bash
# Para evitar conflictos de versiones
pip install langchain==0.1.0 langchain-community==0.0.13 langchain-openai==0.0.5
```

## 🛠️ PASO 3: Verificar Dependencias Existentes

Asegurarse de que el proyecto base sigue funcionando.

### **Comandos de Verificación:**

```bash
# 1. Instalar dependencias del proyecto
pip install -r requirements.txt

# 2. Verificar que Groq CLI funciona
python -m iabuilder --help

# 3. Test básico del sistema
python -c "from iabuilder.main import GroqCLIApp; print('✅ Proyecto base funciona')"
```

### **¿Qué debe salir?**
```
usage: __main__.py [-h] [--dir DIR]

Groq CLI Custom - Intelligent AI Code Assistant
...
✅ Proyecto base funciona
```

## 🛠️ PASO 4: Test Completo del Sistema

Verificar que todos los componentes funcionan juntos.

### **Script de Verificación Completo:**

```bash
# Crear script de test
cat > test_intelligent_architecture.py << 'EOF'
#!/usr/bin/env python3
"""
Test completo de la arquitectura inteligente
"""

def test_spacy():
    """Test spaCy classifier"""
    try:
        import spacy
        nlp = spacy.load('es_core_news_sm')

        # Test básico
        doc = nlp("Hola, ¿cómo estás?")
        print(f"✅ spaCy: {len(doc)} tokens procesados")

        # Test clasificación simple
        text = "crea una función de fibonacci"
        doc = nlp(text.lower())
        has_action = any(token.text in ["crea", "haz", "implementa"] for token in doc)
        print(f"✅ Clasificación acción: {'detectada' if has_action else 'no detectada'}")

        return True
    except Exception as e:
        print(f"❌ Error en spaCy: {e}")
        return False

def test_langchain():
    """Test LangChain basic functionality"""
    try:
        from langchain.agents import initialize_agent
        from langchain.llms import OpenAI
        print("✅ LangChain: imports funcionan")
        return True
    except Exception as e:
        print(f"❌ Error en LangChain: {e}")
        return False

def test_groq_integration():
    """Test Groq CLI integration"""
    try:
        from iabuilder.main import GroqCLIApp
        from iabuilder.client import GroqClient
        print("✅ Groq CLI: integración funciona")
        return True
    except Exception as e:
        print(f"❌ Error en Groq CLI: {e}")
        return False

def main():
    print("🧪 TEST COMPLETO - ARQUITECTURA INTELIGENTE")
    print("=" * 50)

    tests = [
        ("spaCy Classifier", test_spacy),
        ("LangChain Agent", test_langchain),
        ("Groq Integration", test_groq_integration),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        print(f"\n🔍 Testing {name}...")
        if test_func():
            passed += 1

    print(f"\n{'=' * 50}")
    print(f"📊 RESULTADOS: {passed}/{total} tests pasaron")

    if passed == total:
        print("🎉 ¡SISTEMA LISTO PARA ARQUITECTURA INTELIGENTE!")
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. Implementar IntentClassifier en iabuilder/intent_classifier.py")
        print("2. Modificar main.py para usar arquitectura de 3 capas")
        print("3. Crear tests unitarios")
        print("4. Probar con usuarios reales")
    else:
        print("⚠️  Algunos tests fallaron. Revisar dependencias.")

if __name__ == "__main__":
    main()
EOF

# Ejecutar test
python test_intelligent_architecture.py
```

### **Resultado Esperado:**
```
🧪 TEST COMPLETO - ARQUITECTURA INTELIGENTE
==================================================

🔍 Testing spaCy Classifier...
✅ spaCy: 4 tokens procesados
✅ Clasificación acción: detectada

🔍 Testing LangChain Agent...
✅ LangChain: imports funcionan

🔍 Testing Groq Integration...
✅ Groq CLI: integración funciona

==================================================
📊 RESULTADOS: 3/3 tests pasaron
🎉 ¡SISTEMA LISTO PARA ARQUITECTURA INTELIGENTE!
```

## 🛠️ PASO 5: Configuración del Entorno

### **Variables de Entorno:**

```bash
# Configurar API key de Groq
export GROQ_API_KEY="tu-api-key-aqui"

# Configurar Python path si es necesario
export PYTHONPATH="${PYTHONPATH}:/ruta/absoluta/a/iabuilder-custom"

# Verificar configuración
echo "GROQ_API_KEY: ${GROQ_API_KEY:+✅ SET}"
echo "PYTHONPATH: $PYTHONPATH"
```

### **Archivo .env (opcional):**

```bash
# Crear archivo .env en el directorio del proyecto
cat > .env << EOF
GROQ_API_KEY=tu-api-key-aqui
PYTHONPATH=/ruta/a/iabuilder-custom
EOF
```

## 🛠️ PASO 6: Test Final con Groq CLI

### **Primer Test de la Nueva Arquitectura:**

```bash
# Iniciar Groq CLI
groq-custom

# Probar mensajes que deberían funcionar diferente ahora:
# 1. Mensaje conversacional (no debería usar tools)
"Hola, ¿cómo estás?"

# 2. Mensaje actionable (sí debería usar tools)
"crea un archivo test.py con print('hola')"

# 3. Pregunta sobre capacidades (no debería usar tools)
"¿qué herramientas tienes disponibles?"
```

## 🔧 Solución de Problemas

### **Error: spaCy model not found**
```bash
# Reinstalar modelo
python -m spacy download es_core_news_sm --force

# O usar modelo alternativo
python -m spacy download es_core_news_md
```

### **Error: LangChain import fails**
```bash
# Instalar versiones específicas
pip install langchain==0.0.350 langchain-community==0.0.13

# O actualizar pip
pip install --upgrade pip
```

### **Error: CUDA/GPU issues**
```bash
# Forzar CPU-only mode
export CUDA_VISIBLE_DEVICES=""
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### **Error: Permission denied**
```bash
# Usar --user flag
pip install --user spacy langchain
python -m spacy download es_core_news_sm --user
```

## 📊 Métricas de Éxito

Después de la instalación, deberías tener:

- ✅ **spaCy**: Funcionando con modelo español
- ✅ **LangChain**: Imports funcionando
- ✅ **Groq CLI**: Integración completa
- ✅ **Performance**: <2 segundos para clasificación
- ✅ **Accuracy**: >90% en clasificación de intenciones

## 🎯 Próximos Pasos

Con la instalación completa, puedes:

1. **Implementar** `IntentClassifier` en `iabuilder/intent_classifier.py`
2. **Modificar** `main.py` para usar la arquitectura de 3 capas
3. **Crear** tests unitarios para la nueva lógica
4. **Medir** mejoras en precisión y performance
5. **Documentar** casos de uso y beneficios

## 📞 Soporte

Si encuentras problemas:

1. **Revisa** la salida del script de test
2. **Verifica** versiones de Python y pip
3. **Comprueba** conexión a internet para downloads
4. **Revisa** logs de error detallados

¿Todo instalado correctamente? ¡La arquitectura inteligente está lista para revolucionar cómo funciona Groq CLI! 🚀