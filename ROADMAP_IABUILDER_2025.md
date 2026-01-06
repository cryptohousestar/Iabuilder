# ROADMAP IABUILDER 2025
## Intelligent Architecture Builder - Plan de Desarrollo Completo

**Autor:** Ivan Gonzalez
**Herramienta de desarrollo:** Claude CLI (Opus)
**Fecha inicio proyecto:** 24 Diciembre 2024
**Fecha roadmap:** 27 Diciembre 2024
**Versión actual:** 0.1.0-alpha

---

## VISIÓN DEL PROYECTO

**IABuilder** es una herramienta CLI de desarrollo asistido por IA con soporte multi-proveedor (Groq, OpenAI, Anthropic, Google, OpenRouter). El objetivo es crear una herramienta profesional, compilable en C, con instalador para Linux.

### Objetivos a Largo Plazo:
1. **CLI profesional** - Estable, rápido, confiable
2. **Compilación nativa** - Binario en C para máximo rendimiento
3. **Instalador Linux** - .deb, .rpm, AppImage, snap
4. **Arquitectura limpia** - Modular, testeable, mantenible
5. **Multi-proveedor** - Cualquier LLM compatible con OpenAI API
6. **Windows-ready** - Código preparado para portar a Windows en el futuro

### Filosofía de Desarrollo:
- **Target actual:** Linux
- **Código nuevo:** Compatible con Windows (paths, APIs abstractas)
- **Futuro:** Portar a Windows cuando Linux esté completo

---

## FASE 0: ESTADO ACTUAL (Completado)
**Duración:** 3 días (24-27 Dic 2024)

### Logros:
- [x] CLI funcional con Groq como provider principal
- [x] Sistema multi-proveedor (Groq, OpenAI, Anthropic, Google, OpenRouter)
- [x] 43 herramientas implementadas
- [x] Sistema de tools con function calling
- [x] Exploración automática de proyectos
- [x] Rate limiting
- [x] Clasificador de intents con spaCy
- [x] Renombrado completo: groq_cli → iabuilder

### Problemas Identificados:
- [ ] main.py con 2,357 líneas (debe ser ~300)
- [ ] 7.5% cobertura de tests (debe ser 80%+)
- [ ] Manejo de errores inconsistente
- [ ] API keys en base64 (inseguro)
- [ ] Archivos obsoletos (main_backup.py, etc.)
- [ ] Documentación dispersa

---

## FASE 1: LIMPIEZA Y REFACTORIZACIÓN
**Duración estimada:** 1 semana
**Objetivo:** Código limpio, modular, testeable

### Sprint 1.1: Limpieza Inicial (1-2 días)
```
Tareas:
├── [ ] Eliminar main_backup.py
├── [ ] Eliminar archivos SPRINT_*.md obsoletos
├── [ ] Consolidar tests en /tests/
│   ├── tests/unit/
│   ├── tests/integration/
│   └── tests/fixtures/
├── [ ] Limpiar __pycache__ y .pyc
└── [ ] Actualizar .gitignore
```

### Sprint 1.2: Refactorización de main.py (3-4 días)
```
Estructura objetivo:
iabuilder/
├── core/
│   ├── __init__.py
│   ├── app.py              # 200 líneas - Clase IABuilderApp simplificada
│   ├── bootstrap.py        # 100 líneas - Inicialización y configuración
│   └── shutdown.py         # 50 líneas - Cleanup y signal handlers
│
├── chat/
│   ├── __init__.py
│   ├── handler.py          # 150 líneas - Manejo de mensajes
│   ├── router.py           # 100 líneas - Routing por tipo de intent
│   └── responses.py        # 100 líneas - Respuestas conversacionales
│
├── ai/
│   ├── __init__.py
│   ├── client.py           # Ya existe - Cliente API
│   ├── response_processor.py   # 150 líneas - Procesar respuestas AI
│   ├── tool_executor.py    # 150 líneas - Ejecutar tools
│   └── retry_handler.py    # 80 líneas - Retries y fallbacks
│
├── errors/
│   ├── __init__.py
│   ├── handler.py          # 100 líneas - Manejo centralizado
│   ├── exceptions.py       # 80 líneas - Excepciones custom
│   └── logging.py          # 50 líneas - Configuración de logs
│
└── main.py                 # 50 líneas - Solo entry point
```

### Sprint 1.3: Sistema de Errores (1 día)
```
Implementar:
├── [ ] Logger centralizado con rotación de archivos
├── [ ] Excepciones tipadas (ToolError, APIError, ConfigError)
├── [ ] Error recovery automático
├── [ ] Reporte de errores para debugging
└── [ ] Eliminar todos los "except: pass"
```

### Entregables Fase 1:
- [ ] main.py reducido a ~50 líneas
- [ ] Código distribuido en módulos de 100-200 líneas
- [ ] Sistema de logging funcional
- [ ] Zero "pass" statements silenciosos
- [ ] Tests básicos para cada módulo nuevo

---

## FASE 2: SEGURIDAD Y CONFIGURACIÓN
**Duración estimada:** 1 semana
**Objetivo:** Seguridad robusta, configuración flexible

### Sprint 2.1: Gestión de Credenciales (2 días)
```
Implementar:
├── [ ] Keyring del sistema (principal) - funciona en Linux y Windows
├── [ ] Variables de entorno (fallback universal)
├── [ ] Archivo de config (fallback final)
├── [ ] Migración automática de base64 → keyring
└── [ ] Abstracción de paths para Windows-ready
```

**Código ejemplo:**
```python
# security/credentials.py
import os
import platform
from pathlib import Path

class CredentialManager:
    """Gestión de credenciales - Linux ahora, Windows-ready."""

    def get_api_key(self, provider: str) -> str:
        # 1. Variable de entorno (siempre funciona)
        env_var = f"{provider.upper()}_API_KEY"
        if env_var in os.environ:
            return os.environ[env_var]

        # 2. Keyring del sistema (Linux/Windows/macOS)
        try:
            import keyring
            key = keyring.get_password("iabuilder", provider)
            if key:
                return key
        except Exception:
            pass

        # 3. Archivo de config (fallback)
        return self._read_from_config(provider)

    def save_api_key(self, provider: str, key: str):
        try:
            import keyring
            keyring.set_password("iabuilder", provider, key)
        except Exception:
            self._save_to_config(provider, key)

    @staticmethod
    def get_config_dir() -> Path:
        """Retorna directorio de config según OS."""
        if platform.system() == "Windows":
            return Path(os.environ.get("APPDATA", "")) / "iabuilder"
        return Path.home() / ".iabuilder"
```

### Sprint 2.2: Validación de Entrada (2 días)
```
Implementar:
├── [ ] Sanitización de paths (prevenir path traversal)
├── [ ] Validación de comandos bash (prevenir injection)
├── [ ] Límites de tamaño para archivos
├── [ ] Rate limiting por usuario
└── [ ] Timeout para operaciones largas
```

### Sprint 2.3: Configuración Mejorada (2 días)
```
Estructura:
~/.iabuilder/
├── config.yaml           # Configuración general
├── providers.yaml.enc    # Providers encriptados
├── models.json          # Cache de modelos
├── history/             # Historial de conversaciones
├── logs/                # Logs rotados
└── keys/                # Claves de encriptación
```

### Entregables Fase 2:
- [ ] API keys encriptadas con Fernet
- [ ] Validación completa de inputs
- [ ] Configuración documentada
- [ ] Sin credenciales en texto plano

---

## FASE 3: TESTING COMPREHENSIVO
**Duración estimada:** 1 semana
**Objetivo:** 80%+ cobertura, CI/CD preparado

### Sprint 3.1: Estructura de Tests (1 día)
```
tests/
├── conftest.py              # Fixtures compartidos
├── unit/
│   ├── test_core_app.py
│   ├── test_chat_handler.py
│   ├── test_ai_processor.py
│   ├── test_tool_executor.py
│   ├── test_error_handler.py
│   └── test_credentials.py
├── integration/
│   ├── test_full_conversation.py
│   ├── test_tool_chain.py
│   └── test_provider_switching.py
├── fixtures/
│   ├── mock_responses.json
│   ├── sample_projects/
│   └── test_files/
└── performance/
    ├── test_response_time.py
    └── test_memory_usage.py
```

### Sprint 3.2: Tests Unitarios (3 días)
```
Cobertura objetivo por módulo:
├── core/          → 90%
├── chat/          → 85%
├── ai/            → 80%
├── errors/        → 95%
├── tools/         → 75%
├── providers/     → 80%
└── config/        → 85%
```

### Sprint 3.3: Tests de Integración (2 días)
```
Escenarios:
├── [ ] Conversación completa (5 turnos)
├── [ ] Ejecución de 10 tools en secuencia
├── [ ] Cambio de provider mid-session
├── [ ] Recovery de errores de API
├── [ ] Timeout y retry handling
└── [ ] Concurrencia (múltiples requests)
```

### Sprint 3.4: CI/CD con GitHub Actions (1 día)
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Run tests
        run: pytest --cov=iabuilder --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Entregables Fase 3:
- [ ] 80%+ cobertura de tests
- [ ] CI/CD funcionando en GitHub
- [ ] Badges de coverage en README
- [ ] Tests automatizados en cada push

---

## FASE 4: OPTIMIZACIÓN DE RENDIMIENTO
**Duración estimada:** 1 semana
**Objetivo:** Preparar para compilación, máxima velocidad

### Sprint 4.1: Profiling y Benchmarks (2 días)
```
Métricas a medir:
├── Tiempo de inicio de la app
├── Tiempo de respuesta por request
├── Uso de memoria peak
├── Tiempo de ejecución de tools
└── Latencia de API calls
```

### Sprint 4.2: Optimizaciones Python (3 días)
```
Implementar:
├── [ ] LRU Cache para operaciones frecuentes
├── [ ] Lazy loading de módulos pesados
├── [ ] Connection pooling para APIs
├── [ ] Async/await para operaciones I/O
├── [ ] Generators en lugar de listas grandes
└── [ ] __slots__ en clases frecuentes
```

**Ejemplo de optimización:**
```python
# ANTES (lento)
def get_all_files():
    return list(Path('.').rglob('*'))  # Carga todo en memoria

# DESPUÉS (rápido)
def get_all_files():
    yield from Path('.').rglob('*')  # Generator, memoria O(1)
```

### Sprint 4.3: Caché Inteligente (2 días)
```python
# cache/smart_cache.py
from functools import lru_cache
from diskcache import Cache

class SmartCache:
    def __init__(self):
        self.memory_cache = {}  # Hot data
        self.disk_cache = Cache('~/.iabuilder/cache')  # Persistent

    def get(self, key, compute_fn, ttl=3600):
        # 1. Check memory
        # 2. Check disk
        # 3. Compute and store
```

### Entregables Fase 4:
- [ ] Benchmarks documentados
- [ ] Tiempo de inicio < 1 segundo
- [ ] Response time < 100ms (sin API)
- [ ] Memoria < 100MB en uso normal

---

## FASE 5: PREPARACIÓN PARA COMPILACIÓN
**Duración estimada:** 2 semanas
**Objetivo:** Código listo para Cython/Nuitka

### Sprint 5.1: Type Hints Completos (3 días)
```python
# ANTES
def process_message(message, context):
    return result

# DESPUÉS
def process_message(
    message: str,
    context: MessageContext
) -> ProcessingResult:
    return result
```

```
Archivos a tipar:
├── core/*.py        → 100% typed
├── chat/*.py        → 100% typed
├── ai/*.py          → 100% typed
├── tools/*.py       → 90% typed
└── providers/*.py   → 100% typed
```

### Sprint 5.2: Eliminar Dependencias Dinámicas (2 días)
```
Problemas a resolver:
├── [ ] Eliminar exec() y eval()
├── [ ] Eliminar importlib dinámico donde posible
├── [ ] Reemplazar __getattr__ dinámico
├── [ ] Usar Protocols en lugar de duck typing
└── [ ] Documentar dependencias irremovibles
```

### Sprint 5.3: Compilación con Cython (4 días)
```
Estructura:
├── setup_cython.py          # Configuración de compilación
├── iabuilder/*.pyx          # Módulos Cython (críticos)
├── iabuilder/*.py           # Módulos Python (compatibilidad)
└── build/
    └── lib.linux-x86_64/    # Binarios compilados
```

**setup_cython.py:**
```python
from setuptools import setup
from Cython.Build import cythonize

setup(
    name="iabuilder",
    ext_modules=cythonize([
        "iabuilder/core/*.py",
        "iabuilder/ai/*.py",
        "iabuilder/chat/*.py",
    ], compiler_directives={
        'language_level': "3",
        'boundscheck': False,
        'wraparound': False,
    }),
)
```

### Sprint 5.4: Compilación con Nuitka (3 días)
```bash
# Compilación standalone
python -m nuitka \
    --standalone \
    --onefile \
    --linux-onefile-icon=assets/icon.png \
    --output-filename=iabuilder \
    --include-package=iabuilder \
    --include-package=groq \
    --include-package=prompt_toolkit \
    iabuilder/main.py
```

### Entregables Fase 5:
- [ ] 100% type hints en módulos core
- [ ] Compilación Cython funcionando
- [ ] Compilación Nuitka funcionando
- [ ] Binario standalone de ~50-100MB
- [ ] Performance 2-3x más rápido

---

## FASE 6: EMPAQUETADO E INSTALADORES
**Duración estimada:** 2 semanas
**Objetivo:** Instaladores profesionales para Linux

### Sprint 6.1: Estructura de Distribución (2 días)
```
dist/
├── linux/
│   ├── deb/                 # Debian/Ubuntu
│   ├── rpm/                 # Fedora/RHEL
│   ├── appimage/            # AppImage universal
│   ├── snap/                # Snap package
│   └── flatpak/             # Flatpak
├── scripts/
│   ├── install.sh           # Instalador universal
│   ├── uninstall.sh         # Desinstalador
│   └── update.sh            # Actualizador
└── assets/
    ├── icon.png
    ├── icon.svg
    └── desktop/
        └── iabuilder.desktop
```

### Sprint 6.2: Paquete .deb (3 días)
```
iabuilder_1.0.0_amd64/
├── DEBIAN/
│   ├── control
│   ├── postinst
│   ├── prerm
│   └── conffiles
├── usr/
│   ├── bin/
│   │   └── iabuilder        # Binario
│   ├── lib/
│   │   └── iabuilder/       # Librerías
│   └── share/
│       ├── applications/
│       │   └── iabuilder.desktop
│       ├── icons/
│       │   └── iabuilder.png
│       └── doc/
│           └── iabuilder/
└── etc/
    └── iabuilder/
        └── config.yaml.example
```

**DEBIAN/control:**
```
Package: iabuilder
Version: 1.0.0
Section: devel
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.8), libssl3
Maintainer: Ivan Gonzalez <admin@iabuilder.app>
Description: Intelligent Architecture Builder
 AI-powered development CLI with multi-provider support.
 Works with Groq, OpenAI, Anthropic, Google, and more.
```

### Sprint 6.3: AppImage Universal (2 días)
```yaml
# AppImageBuilder.yml
version: 1
AppDir:
  path: ./AppDir
  app_info:
    id: app.iabuilder.IABuilder
    name: IABuilder
    icon: iabuilder
    version: 1.0.0
    exec: usr/bin/iabuilder
  runtime:
    env:
      PYTHONHOME: '${APPDIR}/usr'
      PYTHONPATH: '${APPDIR}/usr/lib/python3.11'
```

### Sprint 6.4: Snap Package (2 días)
```yaml
# snapcraft.yaml
name: iabuilder
version: '1.0.0'
summary: AI-powered development CLI
description: |
  Intelligent Architecture Builder with multi-provider LLM support.

grade: stable
confinement: classic

parts:
  iabuilder:
    plugin: python
    source: .
    python-packages:
      - groq
      - prompt-toolkit
      - rich

apps:
  iabuilder:
    command: bin/iabuilder
```

### Sprint 6.5: Script de Instalación Universal (1 día)
```bash
#!/bin/bash
# install.sh - Instalador universal para IABuilder

set -e

VERSION="1.0.0"
INSTALL_DIR="/opt/iabuilder"
BIN_LINK="/usr/local/bin/iabuilder"

echo "╔════════════════════════════════════════════╗"
echo "║     IABuilder Installer v${VERSION}            ║"
echo "╚════════════════════════════════════════════╝"

# Detectar distribución
if [ -f /etc/debian_version ]; then
    echo "📦 Detectado: Debian/Ubuntu"
    sudo apt update
    sudo dpkg -i iabuilder_${VERSION}_amd64.deb
elif [ -f /etc/redhat-release ]; then
    echo "📦 Detectado: RHEL/Fedora"
    sudo dnf install iabuilder-${VERSION}.x86_64.rpm
else
    echo "📦 Instalación genérica"
    sudo mkdir -p $INSTALL_DIR
    sudo cp -r . $INSTALL_DIR/
    sudo ln -sf $INSTALL_DIR/iabuilder $BIN_LINK
fi

echo "✅ IABuilder instalado correctamente"
echo "🚀 Ejecuta: iabuilder"
```

### Entregables Fase 6:
- [ ] Paquete .deb para Debian/Ubuntu
- [ ] Paquete .rpm para Fedora/RHEL
- [ ] AppImage universal
- [ ] Snap package
- [ ] Script de instalación universal
- [ ] Documentación de instalación

---

## FASE 7: DOCUMENTACIÓN Y RELEASE
**Duración estimada:** 1 semana
**Objetivo:** Documentación completa, release 1.0

### Sprint 7.1: Documentación de Usuario (2 días)
```
docs/
├── getting-started/
│   ├── installation.md
│   ├── first-steps.md
│   └── configuration.md
├── guides/
│   ├── providers.md
│   ├── tools.md
│   ├── customization.md
│   └── troubleshooting.md
├── reference/
│   ├── commands.md
│   ├── api.md
│   └── config-options.md
└── development/
    ├── contributing.md
    ├── architecture.md
    └── building.md
```

### Sprint 7.2: Documentación de API (2 días)
```python
# Usar Sphinx + autodoc
# docs/conf.py
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]
```

### Sprint 7.3: Release 1.0.0 (3 días)
```
Checklist de Release:
├── [ ] Changelog completo
├── [ ] Version bumped a 1.0.0
├── [ ] Tests passing (100%)
├── [ ] Coverage > 80%
├── [ ] Binarios compilados
├── [ ] Paquetes creados
├── [ ] Documentación publicada
├── [ ] GitHub Release creado
├── [ ] Anuncio en redes
└── [ ] Backup del código
```

### Entregables Fase 7:
- [ ] Documentación completa en docs/
- [ ] README actualizado
- [ ] CHANGELOG.md
- [ ] Release 1.0.0 en GitHub
- [ ] Binarios publicados

---

## CALENDARIO ESTIMADO

```
Semana 1 (Dic 28 - Ene 3):   FASE 1 - Limpieza y Refactorización
Semana 2 (Ene 4 - Ene 10):   FASE 2 - Seguridad y Configuración
Semana 3 (Ene 11 - Ene 17):  FASE 3 - Testing Comprehensivo
Semana 4 (Ene 18 - Ene 24):  FASE 4 - Optimización de Rendimiento
Semana 5-6 (Ene 25 - Feb 7): FASE 5 - Preparación para Compilación
Semana 7-8 (Feb 8 - Feb 21): FASE 6 - Empaquetado e Instaladores
Semana 9 (Feb 22 - Feb 28):  FASE 7 - Documentación y Release

🎯 RELEASE 1.0.0: ~28 Febrero 2025
```

---

## MÉTRICAS DE ÉXITO

### Código:
| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Líneas en main.py | 2,357 | <100 |
| Cobertura tests | 7.5% | 80%+ |
| Type hints | ~20% | 100% |
| Complejidad ciclomática | 40-60 | <10 |

### Rendimiento:
| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Tiempo de inicio | ~3s | <1s |
| Memoria en uso | ~150MB | <100MB |
| Tamaño binario | N/A | <100MB |

### Distribución:
| Formato | Estado | Objetivo |
|---------|--------|----------|
| .deb | ❌ | ✅ |
| .rpm | ❌ | ✅ |
| AppImage | ❌ | ✅ |
| Snap | ❌ | ✅ |
| Binario standalone | ❌ | ✅ |

---

## NOTAS DE TRABAJO CON CLAUDE CLI

### Comandos Útiles:
```bash
# Refactorización
"refactoriza main.py en módulos separados siguiendo el roadmap"

# Tests
"crea tests unitarios para el módulo chat/handler.py"

# Compilación
"configura Cython para compilar el módulo core/"

# Empaquetado
"crea el archivo DEBIAN/control para el paquete .deb"
```

### Mejores Prácticas:
1. **Commits frecuentes** - Después de cada tarea completada
2. **Tests primero** - Escribir tests antes de refactorizar
3. **Documentar cambios** - Actualizar CHANGELOG.md
4. **Backup regular** - Antes de cambios grandes
5. **Verificar imports** - Después de mover código

---

## PRÓXIMOS PASOS INMEDIATOS

### HOY (27 Dic 2024):
1. [ ] Eliminar main_backup.py
2. [ ] Crear estructura de carpetas core/, chat/, ai/, errors/
3. [ ] Empezar extracción de error handling

### MAÑANA (28 Dic 2024):
1. [ ] Continuar refactorización de main.py
2. [ ] Crear primeros tests para módulos nuevos
3. [ ] Configurar logging centralizado

### ESTA SEMANA:
1. [ ] Completar FASE 1
2. [ ] main.py reducido a <100 líneas
3. [ ] Tests básicos funcionando

---

**Documento vivo** - Actualizar según avance el proyecto

*Generado con Claude CLI (Opus) - 27 Diciembre 2024*
