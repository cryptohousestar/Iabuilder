# 🧪 INSTRUCCIONES DE TESTING - Groq CLI Refactorizado

## 🚀 PASO 1: Reinstalar

```bash
cd "/home/linuxpc/Desktop/groq cli custom"
pip install -e .
```

## 🎯 PASO 2: Prueba Básica

### Test 1: Iniciar en directorio de prueba
```bash
cd ~/Desktop/groq\ cli\ custom
groq-custom
```

**Deberías ver:**
```
✅ Atomic tools registered (Claude CLI style)
📂 Scanned directory: groq cli custom
   Found: X files, Y directories
```

### Test 2: Verificar herramientas registradas
Cuando inicie, debería mostrar algo como:
```
🔧 Registered tools:
  • read_file, write_file, edit_file
  • execute_bash, run_python
  • grep_search, glob_search, web_search
  • http_request
  • git_status, git_commit, git_branch, git_log, git_remote
```

**Conteo esperado:** 15-25 herramientas (dependiendo del proyecto)

---

## 🧪 PASO 3: Tests de Funcionalidad

### Test 3.1: Comando simple (ejecutar bash)
```
Usuario> lista los archivos
```

**Esperado:**
- ✅ Debería ejecutar: `execute_bash(command="ls -la")`
- ✅ Debería mostrar: "🔧 Tool execute_bash executed"
- ✅ Debería mostrar el output del comando

### Test 3.2: Leer archivo
```
Usuario> lee el archivo README.md
```

**Esperado:**
- ✅ Debería ejecutar: `read_file(file_path="README.md")`
- ✅ Debería mostrar el contenido del README

### Test 3.3: Crear archivo
```
Usuario> crea un archivo test.txt con el texto "Hola Mundo"
```

**Esperado:**
- ✅ Debería ejecutar: `write_file(file_path="test.txt", content="Hola Mundo")`
- ✅ Debería confirmar que el archivo fue creado

### Test 3.4: Git status (si estás en un repo)
```
Usuario> git status
```

**Esperado:**
- ✅ Debería ejecutar: `git_status()`
- ✅ Debería mostrar el estado del repositorio

### Test 3.5: Búsqueda de archivos
```
Usuario> busca archivos python
```

**Esperado:**
- ✅ Debería ejecutar: `glob_search(pattern="*.py")` o similar
- ✅ Debería listar archivos .py encontrados

### Test 3.6: Saludo (NO debería usar tools)
```
Usuario> hola
```

**Esperado:**
- ✅ NO debería ejecutar tools
- ✅ Debería responder conversacionalmente
- ✅ NO debería mostrar "🔧 Tool executed"

---

## 📊 PASO 4: Verificar Métricas

### Métrica 1: Tool Usage Rate
De 10 comandos de prueba (excluyendo saludos), deberías ver:
- **Target:** 9-10 comandos usan tools (90-100%)
- **Antes del refactoring:** ~7 comandos usaban tools (70%)

### Métrica 2: Tiempo de respuesta
- **Inicio del CLI:** <2 segundos
- **Escaneo de directorio (`ls`):** <1 segundo
- **Primera respuesta:** <5 segundos

### Métrica 3: Herramientas registradas
```bash
# Al inicio, contar cuántas herramientas se registraron
# Debería ser 15-25 dependiendo del proyecto
```

---

## 🐛 PASO 5: Debugging (si algo falla)

### Debug 1: Ver herramientas registradas
Agrega esta línea temporal al final de `_setup_intelligent_tools()`:
```python
print(f"DEBUG: Registered {len(get_tool_registry().get_schemas())} tools")
for tool in get_tool_registry().get_schemas():
    print(f"  - {tool['function']['name']}")
```

### Debug 2: Ver si `_message_needs_tools()` funciona
Agrega debug en `_handle_chat_message()`:
```python
needs_tools = self._message_needs_tools(message)
print(f"DEBUG: Message '{message}' needs_tools={needs_tools}")
```

### Debug 3: Ver intent classification
```python
intent = self.intent_classifier.classify(message)
print(f"DEBUG: Intent classified as: {intent}")
```

---

## ✅ PASO 6: Checklist de Éxito

Marca cada item cuando pase el test:

- [ ] CLI inicia sin errores
- [ ] Muestra "✅ Atomic tools registered"
- [ ] Ejecuta `ls` automáticamente al inicio
- [ ] Muestra "Found: X files, Y directories"
- [ ] Registra 15-25 herramientas (dependiendo del proyecto)
- [ ] Comando "lista archivos" ejecuta `execute_bash`
- [ ] Comando "lee README.md" ejecuta `read_file`
- [ ] Comando "git status" ejecuta `git_status` (si hay .git/)
- [ ] Saludo "hola" NO ejecuta tools
- [ ] Tool Usage Rate >90%

---

## 🔥 PASO 7: Test de Comparación con Claude CLI

Para verificar que funciona igual que Claude CLI:

### Misma solicitud en ambos:
```
Usuario> analiza el proyecto y dime qué archivos importantes hay
```

**Claude CLI hace:**
1. Usa herramientas de búsqueda para explorar
2. Lee archivos importantes (README, package.json, etc.)
3. Resume la información

**Groq CLI refactorizado debería hacer:**
1. ✅ Ya tiene contexto inicial (`ls` automático)
2. ✅ Debería usar `glob_search` o `grep_search`
3. ✅ Debería usar `read_file` para archivos clave
4. ✅ Debería resumir la información

---

## 📝 REPORTAR RESULTADOS

Si todo funciona, deberías ver:
```
✅ FASE 1: LangChain eliminado
✅ FASE 2: Herramientas atómicas registradas
✅ FASE 3: System prompt actualizado
✅ FASE 4: ls automático funciona
✅ FASE 5: _message_needs_tools() simplificado
✅ FASE 6: Tests pasados

🎉 REFACTORING COMPLETO - Tool Usage >90%
```

Si algo falla, revisa:
1. `REFACTORING_CHANGELOG.md` - Documentación de cambios
2. Logs de error en consola
3. Debug prints sugeridos arriba
