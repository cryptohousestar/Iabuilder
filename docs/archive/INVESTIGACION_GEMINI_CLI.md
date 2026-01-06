# Investigación: Comparación Gemini CLI vs IABuilder

## Objetivo
Identificar por qué Gemini CLI funciona excelente con function calling y por qué IABuilder aún tiene problemas. Esta investigación fue realizada el 2026-01-03.

## 1. ARQUITECTURA COMPARATIVA

### Gemini CLI (Google Oficial)
- **Repository**: [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)
- **API**: SDK `@google/genai` directo (formato nativo de Gemini)
- **Lenguaje**: TypeScript
- **Herramientas**: Shell, ReadFile, EditFile, ReadManyFiles, WebSearch, MCP support
- **Flujo**: Modelo → functionCall → Ejecutar → functionResponse

### IABuilder (Nuestro proyecto)
- **API**: OpenAI SDK → OpenRouter → Gemini (API intermediaria)
- **Lenguaje**: Python
- **Herramientas**: 5 herramientas (bash, read_file, write_file, edit_file, web_search)
- **Flujo**: Modelo → tool_calls → Convertir a texto → Ejecutar → [Resultado de...]

---

## 2. DIFERENCIA CRÍTICA: FORMATO DE TOOL RESULTS

### Gemini CLI (Nativo)
Después de ejecutar una herramienta, envía de vuelta:

```json
{
  "role": "user",
  "parts": [{
    "functionResponse": {
      "name": "execute_bash",
      "response": {
        "stdout": "output here",
        "exit_code": 0
      }
    }
  }]
}
```

**Ventajas:**
- ✅ Formato estructurado que Gemini entiende nativamente
- ✅ El modelo sabe que es una respuesta de función, no texto arbitrario
- ✅ Preserva metadata de la respuesta (exit_code, etc.)

### IABuilder (Actual)
En `conversation.py:290-300`, convertimos a:

```json
{
  "role": "user",
  "content": "[Resultado de execute_bash]:\n{\"success\": true, \"result\": {\"stdout\": \"output\"}}"
}
```

**Problemas:**
- ❌ Es texto plano, el modelo no sabe que es respuesta de herramienta
- ❌ El modelo puede interpretarlo como instrucción del usuario
- ❌ Perdemos el contexto estructurado
- ❌ Causa confusión en el modelo (por eso describe en lugar de actuar)

---

## 3. ARQUITECTURA DE TOOLS EN GEMINI CLI

### Estructura base
En `packages/core/src/tools/`:

```
tool-registry.ts      ← Descubrimiento y registro de tools
tools.ts              ← Definición base de todas las tools
shell.ts              ← Ejecuta comandos (bash -c <command>)
read-file.ts          ← Lee archivos (maneja texto, imágenes, PDFs)
edit.ts               ← Reemplaza contenido en archivos
read-many-files.ts    ← Lee múltiples archivos (overview de codebase)
mcp-client.ts         ← Soporte para MCP servers custom
web-search.ts         ← Búsqueda web
```

### Patrón de Tool Definition

**Gemini CLI** usa:
- `ToolBuilder` interface: Define schema, nombre, descripción
- `ToolInvocation`: Objeto validado listo para ejecutar
- `ToolResult`: Resultado con `llmContent` (para el modelo) y `returnDisplay` (para usuario)
- **Confirmación multi-stage**: ToolConfirmationOutcome con opciones (ProceedOnce, ProceedAlways, Cancel, ModifyWithEditor)

**IABuilder** usa:
- `Tool` base class simple
- Ejecución directa sin validación previa
- Sin sistema de confirmación (solo callback simple)

---

## 4. SYSTEM PROMPT: DIFERENCIA CLAVE

### Gemini CLI Mandates (de `prompts.ts`)

```
⚡ PRIMARY WORKFLOWS:

1. "Delegate to CodebaseInvestigatorAgent for complex refactoring"
2. "Understand requirements → Build grounded plan → Implement → Verify → Finalize"
3. "Add comments sparingly, focusing on 'why' rather than 'what'"
4. "Fulfill requests thoroughly, including adding tests"

⚡ OPERATIONAL GUIDELINES:

- "Use tools for actions; text only for communication"
- "Execute independent tool calls in parallel when feasible"
- "Minimal output (fewer than 3 lines when practical)"
- "Explain critical filesystem-modifying commands beforehand"
- Concise, direct tone suitable for CLI environments
```

### IABuilder (Actual)

```
⚡ REGLA #1: ACTÚA INMEDIATAMENTE, NUNCA PREGUNTES
- Usuario dice X → USA herramienta AHORA
- NUNCA describas lo que VAS a hacer
- USA las herramientas para descubrir lo que necesitas

⚡ REGLA #2: SI UNA HERRAMIENTA FALLA, CORRIGE Y REINTENTA

⚡ REGLA #3: PARA CAMBIOS GRANDES, PLANIFICA PRIMERO
```

**Problemas:**
- ❌ No dice: "Use tools for actions; text only for communication"
- ❌ No dice: "Execute independent tool calls in parallel"
- ❌ No dice: "Minimal output when practical"
- ❌ Demasiado verbose para CLI

---

## 5. EL MISTERIO DE `unknown({})`

### Dónde ocurre

En `conversation.py:268-276`:

```python
for tc in tool_calls:
    if isinstance(tc, dict):
        func = tc.get("function", {})
        name = func.get("name", "unknown")  # ← AQUÍ FALLA
        args = func.get("arguments", "{}")
```

### El problema

Cuando OpenRouter + Gemini devuelve tool_calls, pueden venir en formato:
- OpenAI: `{"id": "...", "function": {"name": "...", "arguments": "..."}}`
- Gemini: `{"name": "...", "args": {...}}`

Nuestro parsing solo busca `function.name`, si no lo encuentra devuelve `"unknown"`.

### Resultado en el historial

El modelo recibe:
```
[Acción: Ejecutando unknown({})]
```

Y se confunde porque no sabe qué tool se ejecutó.

---

## 6. VERIFICACIÓN DE OpenRouter DOCS

Según [OpenRouter Tool Calling Docs](https://openrouter.ai/docs/guides/features/tool-calling):

### Request inicial
```json
{
  "model": "google/gemini-2.5-flash",
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "execute_bash",
        "description": "...",
        "parameters": {...}
      }
    }
  ],
  "messages": [...]
}
```

### Response con tool_calls
```json
{
  "finish_reason": "tool_calls",
  "tool_calls": [
    {
      "type": "function",
      "function": {"name": "execute_bash", "arguments": "..."}
    }
  ]
}
```

### Enviar resultados
```json
{
  "model": "google/gemini-2.5-flash",
  "tools": [...],  # ← ¡DEBE INCLUIRSE EN CADA REQUEST!
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "tool_calls": [...]},
    {"role": "tool", "tool_call_id": "...", "content": "..."}  # ← Formato OpenAI
  ]
}
```

**CRÍTICO**: `tools` debe enviarse en CADA request, incluso cuando enviamos los resultados.

---

## 7. PROBLEMA CON STREAMING + TOOL_CALLS

Hay un [issue conocido](https://discuss.ai.google.dev/t/gemini-openai-compatibility-issue-with-tool-call-streaming/59886) en la compatibilidad OpenAI de Gemini:

- ⚠️ Cuando haces streaming de tool_calls con Gemini vía API OpenAI-compatible, hay problemas
- ⚠️ Algunas respuestas vienen malformadas
- ⚠️ El modelo a veces dice que va a ejecutar pero `tool_calls: False`

**Solución en Gemini CLI**: Usa el SDK nativo sin streaming de tool_calls intermedios.

---

## 8. OPCIÓN: API DIRECTA DE GEMINI

Google ofrece un endpoint OpenAI-compatible:

```
https://generativelanguage.googleapis.com/v1beta/openai/
```

**Ventajas sobre OpenRouter:**
- ✅ Una menos capa de traducción
- ✅ Google controla directamente la traducción
- ✅ Menos latencia
- ✅ Mismo formato que OpenAI pero optimizado para Gemini

**Desventajas:**
- ❌ Solo funciona con Gemini (no es multi-provider como OpenRouter)
- ❌ Requiere API key de Google

---

## 9. CONCLUSIONES

### Por qué Gemini CLI funciona excelente:

1. ✅ **Formato nativo**: Usa `functionResponse` estructurado, no texto plano
2. ✅ **API directa**: Gemini entiende exactamente sus propios mensajes
3. ✅ **System prompt preciso**: "Use tools for actions" es muy claro
4. ✅ **Validación de herramientas**: Pre-valida antes de ejecutar
5. ✅ **Manejo de confirmación**: Usuario puede aprobar antes de ejecutar

### Por qué IABuilder aún tiene problemas:

1. ❌ **Conversión a texto**: Perdemos el contexto de herramienta
2. ❌ **API intermediaria**: OpenRouter traduce, pueden haber errores
3. ❌ **Parsing incompleto**: `unknown({})` cuando formato no coincide
4. ❌ **System prompt genérico**: No dice "Use tools for actions"
5. ❌ **`tools` parameter**: ¿Se envía en cada request?
6. ❌ **Streaming issues**: Problema conocido con Gemini + streaming + tool_calls

---

## 10. RECOMENDACIONES PARA IABUILDER

### Inmediato (High Priority)

1. **Arreglar conversión de tool results**
   - NO convertir `role: "tool"` a `role: "user"`
   - Mantener formato OpenAI estándar
   - OpenRouter entenderá mejor

2. **Arreglar parsing de `unknown({})`**
   - Soportar ambos formatos de tool_calls
   - Gemini + OpenAI compatible

3. **Mejorar system prompt**
   - Agregar: "Use tools for actions; text only for communication"
   - Agregar: "Execute independent tool calls in parallel"
   - Agregar: "Minimal output when practical"

4. **Verificar `tools` en cada request**
   - Asegurar que se envían en Step 1, 2 y 3
   - OpenRouter lo requiere

### Mediano (Medium Priority)

5. **Desactivar streaming de tool_calls**
   - Hay issues conocidos con Gemini
   - Usar streaming solo para contenido de respuesta

6. **Mejorar validación de tools**
   - Validar argumentos ANTES de ejecutar
   - Similar a Gemini CLI

### Largo plazo (Nice to Have)

7. **Opción de API directa de Gemini**
   - `https://generativelanguage.googleapis.com/v1beta/openai/`
   - Alternativa a OpenRouter para usuarios de Gemini
   - Una menos capa de traducción

---

## 11. FUENTES

- [Gemini CLI GitHub](https://github.com/google-gemini/gemini-cli)
- [Gemini API Function Calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Gemini OpenAI Compatibility](https://ai.google.dev/gemini-api/docs/openai)
- [OpenRouter Tool Calling](https://openrouter.ai/docs/guides/features/tool-calling)
- [Known Issue: Gemini OpenAI tool_call streaming](https://discuss.ai.google.dev/t/gemini-openai-compatibility-issue-with-tool-call-streaming/59886)
- [Google GenAI SDK (TypeScript)](https://github.com/google/generative-ai-js)

---

**Investigación completada**: 2026-01-03
**Estado**: Ready for implementation
