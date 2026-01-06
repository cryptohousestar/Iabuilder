# 🎯 RATE LIMITING INTELIGENTE - Groq CLI

## 📊 RESUMEN

Implementado sistema de rate limiting **inteligente por modelo** que:
- ✅ Detecta automáticamente límites según el modelo usado
- ✅ Se actualiza cuando cambias de modelo con `/model`
- ✅ **Muy conservador** (70-80% de límites reales) para evitar cortes
- ✅ Soporta modelos **free** y **paid** de Groq
- ✅ Usa animación de carga cuando espera

---

## 🔧 CÓMO FUNCIONA

### 1. Límites Automáticos por Modelo

Cada modelo tiene límites específicos:

**Ejemplo: llama-3.3-70b-versatile (FREE)**
- Límite real Groq: 30 RPM, 12K TPM
- Límite configurado: **20 RPM, 8K TPM** (70% del límite real)
- **Por qué**: Para evitar cortes y confusión del modelo

**Ejemplo: llama-3.1-8b-instant (FREE)**
- Límite real Groq: 30 RPM, 6K TPM
- Límite configurado: **20 RPM, 4K TPM**

**Ejemplo: llama-3.3-70b-versatile (PAID)**
- Límite real Groq: 1K RPM, 300K TPM
- Límite configurado: **800 RPM, 240K TPM** (80% del límite real)

### 2. Cambio Automático de Límites

Cuando usas `/model`:
```bash
> /model llama-3.1-8b-instant
```

El sistema automáticamente:
1. Cambia el modelo
2. Actualiza los límites de rate limiting
3. Muestra información: `📊 Rate limits updated for llama-3.1-8b-instant: TPM: 4,000 | RPM: 20`

### 3. Prevención de Cortes

El sistema verifica **DOS límites** antes de cada request:

1. **TPM (Tokens por Minuto)**
   - Cuenta cuántos tokens usaste en el último minuto
   - Si estás cerca del límite, espera

2. **RPM (Requests por Minuto)**
   - Cuenta cuántas requests hiciste en el último minuto
   - Si estás cerca del límite, espera

Si alguno se excede → **Espera automática** con animación de carga

---

## 📚 MODELOS SOPORTADOS

### FREE TIER (Configurados Conservadoramente)

| Modelo | RPM | TPM | Notas |
|--------|-----|-----|-------|
| llama-3.3-70b-versatile | 20 | 8K | Modelo principal recomendado |
| llama-3.1-8b-instant | 20 | 4K | Más rápido, menor calidad |
| groq/compound | 20 | 50K | **Límite TPM muy alto** |
| groq/compound-mini | 20 | 50K | Versión mini |
| qwen/qwen3-32b | 40 | 4K | **RPM más alto** |
| moonshotai/kimi-k2-instruct | 40 | 7K | Modelo Kimi |
| openai/gpt-oss-120b | 20 | 5.6K | OSS GPT modelo |
| meta-llama/llama-4-scout-17b | 20 | 20K | Llama 4 Scout |
| whisper-large-v3-turbo | 14 | N/A | Audio (sin TPM) |

### PAID TIER (Developer Plan)

| Modelo | RPM | TPM | Mejora vs Free |
|--------|-----|-----|----------------|
| llama-3.3-70b-versatile | 800 | 240K | **40x RPM, 30x TPM** |
| llama-3.1-8b-instant | 800 | 200K | **40x RPM, 50x TPM** |
| whisper-large-v3-turbo | 320 | N/A | **23x RPM** |

---

## 🎮 COMANDOS

### Ver modelo actual y límites
```bash
> /model
```

### Cambiar modelo (FREE tier)
```bash
> /model llama-3.1-8b-instant
✅ Model changed: llama-3.3-70b-versatile → llama-3.1-8b-instant
📊 Rate limits updated for llama-3.1-8b-instant:
   TPM: 4,000 | RPM: 20
```

### Cambiar a modelo de PAGO (si tienes cuenta paid)
```python
# En el futuro se podría agregar:
> /model llama-3.3-70b-versatile --tier paid
```

---

## ⚠️ COMPORTAMIENTO ANTE LÍMITES

### Escenario 1: Requests Rápidas Consecutivas

```bash
> lee archivo1.txt
> lee archivo2.txt
> lee archivo3.txt
> ... (20 requests en 1 minuto)
> lee archivo21.txt
⠋ Processing... [Esperando ~30 segundos hasta el próximo minuto]
```

**Por qué**: Alcanzaste el límite de 20 RPM (requests/minuto)

### Escenario 2: Request con Muchos Tokens

```bash
> analiza todo el proyecto en detalle
[El modelo usa ~6,000 tokens en su respuesta]
> analiza otro archivo grande
⠋ Processing... [Esperando porque ya usaste ~6K tokens y el límite es 8K TPM]
```

**Por qué**: Alcanzaste ~75% del límite TPM (8,000 tokens/minuto)

### Escenario 3: Modelo con Alto TPM

```bash
> /model groq/compound
📊 Rate limits updated for groq/compound:
   TPM: 50,000 | RPM: 20

> [Puedes hacer requests mucho más grandes sin esperar]
```

**Beneficio**: compound tiene **50K TPM** vs 8K del modelo default

---

## 🔍 DEBUGGING

### Ver uso actual de rate limiting

Agrega temporalmente en `main.py`:
```python
from .rate_limiter import get_rate_limiter

rate_limiter = get_rate_limiter()
usage = rate_limiter.get_current_usage()
print(f"DEBUG Rate Usage: {usage}")
```

Output:
```json
{
  "model": "llama-3.3-70b-versatile",
  "tier": "free",
  "tokens_this_minute": 2450,
  "requests_this_minute": 5,
  "effective_tpm": 8000,
  "effective_rpm": 20,
  "tpm_usage_percentage": 30.6,
  "rpm_usage_percentage": 25.0,
  "can_make_request": true
}
```

### Si el modelo se sigue cortando

**Opción 1**: Reducir más los límites

Edita `model_limits.py`:
```python
"llama-3.3-70b-versatile": ModelLimits(
    rpm=15,      # Reducir de 20 a 15
    tpm=6_000,   # Reducir de 8K a 6K
    ...
)
```

**Opción 2**: Usar modelo con límites más altos
```bash
> /model groq/compound  # 50K TPM vs 8K TPM
```

**Opción 3**: Upgrade a Paid tier
```bash
> /model llama-3.3-70b-versatile --tier paid
# 800 RPM, 240K TPM (vs 20 RPM, 8K TPM free)
```

---

## 📈 OPTIMIZACIONES

### 1. Modelos Rápidos para Tareas Simples

```bash
# Tarea simple: listar archivos
> /model llama-3.1-8b-instant
> lista los archivos del proyecto

# Tarea compleja: análisis profundo
> /model llama-3.3-70b-versatile
> analiza la arquitectura del proyecto
```

### 2. Usar Compound para Alto Volumen

```bash
> /model groq/compound
# TPM: 50K (6x más que default)
# Ideal para: procesar muchos archivos, análisis masivo
```

### 3. Pausas Estratégicas

Si haces muchas requests:
```bash
# Request 1-18: OK
# Request 19: Esperar 5 segundos
# Request 20: Esperar 10 segundos
# Así evitas el límite de 20 RPM
```

---

## 🎯 RECOMENDACIONES

### Para Uso FREE (Default)

1. **Usa llama-3.3-70b-versatile** para desarrollo normal
   - Límites: 20 RPM, 8K TPM
   - Suficiente para la mayoría de tareas

2. **Cambia a compound** si necesitas procesar mucho
   - Límites: 20 RPM, **50K TPM**
   - Ideal para análisis masivo

3. **Si tienes problemas de cortes**:
   - Reduce frecuencia de requests
   - O edita `model_limits.py` para ser más conservador

### Para Uso PAID (Opcional)

1. **Upgrade a Developer Plan** si:
   - Necesitas >20 requests/minuto
   - Procesas proyectos grandes constantemente
   - No quieres esperas

2. **Beneficios**:
   - 40x más RPM (800 vs 20)
   - 30x más TPM (240K vs 8K)
   - Casi sin esperas

---

## ✅ TESTING

### Test 1: Cambio de modelo
```bash
groq-custom
> /model llama-3.1-8b-instant
# Debería mostrar: "📊 Rate limits updated..."
```

### Test 2: Uso intensivo
```bash
> lee README.md
> lee main.py
> lee conversation.py
> ... (hacer 15-18 requests rápidas)
# No debería haber espera aún

> ... (request 20-21)
# Debería mostrar: "⠋ Processing..." y esperar
```

### Test 3: Modelo con alto TPM
```bash
> /model groq/compound
> analiza todo el proyecto [request grande, ~5K tokens]
# Debería funcionar sin espera (50K TPM de límite)
```

---

## 📝 ARCHIVOS MODIFICADOS

1. **`model_limits.py`** (NUEVO)
   - Configuración de límites por modelo
   - FREE y PAID tier
   - Muy conservador (70-80% de límites reales)

2. **`rate_limiter.py`** (ACTUALIZADO)
   - Tracking de RPM y TPM
   - Cambio dinámico de modelo
   - Método `update_model()` para `/model`

3. **`main.py`** (ACTUALIZADO)
   - `switch_model()` ahora actualiza rate limiter
   - Inicialización del rate limiter con modelo default

---

## 🎉 RESULTADO

Ahora tu Groq CLI:
- ✅ **No se corta** porque usa límites conservadores
- ✅ **Funciona bien** con modelos free
- ✅ **Se adapta** automáticamente al modelo
- ✅ **Está listo** para upgrade a paid si lo necesitas

**Prioridad: Que funcione bien > Que sea rápido**
(Configuración conservadora evita cortes y confusión del modelo)
