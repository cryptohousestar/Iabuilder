# Sprint 4.4 & 4.6 - Quick Reference Guide

## New Files Created

### Prompts System
```
iabuilder/prompts/
├── __init__.py          # Package exports
├── base.py              # Base prompt template with strictness levels
└── variants.py          # Model family detection and variants
```

### New Providers
```
iabuilder/providers/
├── mistral.py           # Mistral AI (OpenAI-compatible)
├── together.py          # Together AI (100+ open models)
├── deepseek.py          # DeepSeek (cheap, code-focused)
└── cohere.py            # Cohere (RAG specialist, custom API)
```

---

## Prompt System Quick Start

### Import
```python
from iabuilder.prompts import (
    create_optimized_prompt,
    detect_model_family,
    PromptVariantManager,
    StrictnessLevel
)
```

### Auto-Optimize Prompt
```python
# One-liner to get optimized prompt
prompt = create_optimized_prompt(
    model_name="llama-3.1-8b-instant",
    tools=[...],
    context="Additional context"
)
```

### Detect Model Family
```python
family = detect_model_family("gpt-4o")
# Returns: ModelFamily.GPT4
```

### Custom Prompt Manager
```python
manager = PromptVariantManager("claude-3-5-sonnet")
instructions = manager.get_function_calling_instructions()
strictness = manager.get_recommended_strictness()
examples = manager.get_tool_usage_examples(tools)
```

---

## Model Families Supported

| Family | Models | Recommended Strictness |
|--------|--------|----------------------|
| LLAMA_70B | llama-*-70b, llama-*-405b | DETAILED |
| LLAMA_8B | llama-*-8b, llama-*-13b | MAXIMUM |
| CLAUDE | claude-* | STANDARD |
| GPT4 | gpt-4*, gpt-4o* | STANDARD |
| GPT35 | gpt-3.5* | DETAILED |
| GEMINI | gemini-*, gemma-* | STANDARD |
| QWEN | qwen-* | DETAILED |
| DEEPSEEK | deepseek-* | DETAILED |
| MISTRAL | mistral-*, mixtral-* | DETAILED |
| COMMAND | command-* | STANDARD |

---

## Provider Quick Start

### Mistral AI
```python
from iabuilder.providers import MistralProvider

provider = MistralProvider(api_key="your-mistral-key")

response = await provider.chat_completion(
    messages=[{"role": "user", "content": "Hello"}],
    model="mistral-large-latest",
    tools=[...],
    temperature=0.7
)

# Models: mistral-large-latest, mistral-small-latest, 
#         codestral-latest, open-mixtral-8x7b
```

### Together AI
```python
from iabuilder.providers import TogetherProvider

provider = TogetherProvider(api_key="your-together-key")

response = await provider.chat_completion(
    messages=[{"role": "user", "content": "Hello"}],
    model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    tools=[...],
    top_k=50,  # Custom parameter
    repetition_penalty=1.1  # Custom parameter
)

# 100+ models available, popular ones:
# - meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo
# - Qwen/Qwen2.5-72B-Instruct-Turbo
# - mistralai/Mixtral-8x7B-Instruct-v0.1
```

### DeepSeek
```python
from iabuilder.providers import DeepSeekProvider

provider = DeepSeekProvider(api_key="sk-your-deepseek-key")

response = await provider.chat_completion(
    messages=[{"role": "user", "content": "Write Python code"}],
    model="deepseek-coder",  # Best for code
    tools=[...],
    temperature=0.7
)

# Models: deepseek-chat (V3), deepseek-coder (V2), 
#         deepseek-reasoner (R1)
# 64K context, very cheap (~$0.14/M tokens)
```

### Cohere
```python
from iabuilder.providers import CohereProvider

provider = CohereProvider(api_key="your-cohere-key")

response = await provider.chat_completion(
    messages=[{"role": "user", "content": "Search and summarize"}],
    model="command-r-plus",
    tools=[...],
    documents=[  # RAG documents
        {"text": "...", "title": "..."}
    ],
    preamble="Custom system message"
)

# Models: command-r-plus (best), command-r, command-light
# Specialized for RAG, citations, enterprise
```

---

## Common Operations

### List Available Models
```python
models = await provider.list_available_models()
for model in models:
    print(f"{model['id']}: {model['description']}")
```

### Get Fallback Models (Static)
```python
models = provider.get_fallback_models()
# Returns hardcoded list, no API call
```

### Categorize Models
```python
categories = provider.categorize_models()
# Returns: {'llm': [...], 'code': [...], ...}
```

### Check Function Calling Support
```python
supports = provider.supports_function_calling("model-id")
# Returns: True/False
```

### Switch Model
```python
provider.switch_model("new-model-id")
```

---

## Strictness Levels

### MINIMAL
- ~500 characters
- Bare minimum instructions
- For advanced models (GPT-4, Claude)

### STANDARD (Default)
- ~2,000 characters
- Balanced instructions
- Good for most models

### DETAILED
- ~6,000 characters
- Comprehensive instructions
- For mid-size models (70B, Qwen)

### MAXIMUM
- ~15,000 characters
- Most explicit with examples
- For small models (8B, GPT-3.5)

---

## Error Handling

All providers raise standard exceptions:

```python
from iabuilder.providers import (
    AuthenticationError,  # 401 errors
    RateLimitError,       # 429 errors
    APIError,             # Other errors
    ModelNotFoundError    # Model not available
)

try:
    response = await provider.chat_completion(...)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError:
    print("Rate limit exceeded, wait and retry")
except APIError as e:
    print(f"API error: {e}")
```

---

## Provider Comparison

| Feature | Mistral | Together | DeepSeek | Cohere |
|---------|---------|----------|----------|--------|
| API Format | OpenAI | OpenAI | OpenAI | Custom |
| Models | 6 | 100+ | 3 | 4 |
| Max Context | 128K | 130K | 64K | 128K |
| Function Calling | ✓ | ✓ | ✓ | ✓ |
| Streaming | ✓ | ✓ | ✓ | ✓ |
| Best For | Code, EU | Variety | Cost, Code | RAG |
| Pricing | Medium | Low | Very Low | High |

---

## Integration Example

```python
from iabuilder.prompts import create_optimized_prompt
from iabuilder.providers import DeepSeekProvider

# Initialize provider
provider = DeepSeekProvider(api_key="sk-...")

# Define tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }
    }
]

# Create optimized prompt
system_prompt = create_optimized_prompt(
    model_name="deepseek-chat",
    tools=tools,
    context="You are a weather assistant."
)

# Make request
response = await provider.chat_completion(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "What's the weather in Paris?"}
    ],
    model="deepseek-chat",
    tools=tools
)

# Handle response
if response["choices"][0]["message"].get("tool_calls"):
    # Handle function call
    pass
else:
    # Handle text response
    print(response["choices"][0]["message"]["content"])
```

---

## Tips & Best Practices

### Prompt Optimization
- Let the system auto-detect model family
- Override strictness only when needed
- Add custom instructions for domain-specific tasks
- Include context to improve relevance

### Provider Selection
- **Speed**: Groq
- **Quality**: OpenAI GPT-4, Anthropic Claude
- **Cost**: DeepSeek (10x cheaper)
- **Code**: DeepSeek Coder, Codestral
- **RAG**: Cohere Command R+
- **Variety**: Together AI, OpenRouter
- **EU/GDPR**: Mistral

### Error Handling
- Always implement retry logic for RateLimitError
- Cache fallback models to avoid API calls
- Validate API keys before heavy usage
- Use streaming for long responses

### Performance
- Use smaller models for simple tasks
- Cache system prompts (they're deterministic)
- Batch requests when possible
- Monitor token usage for cost control

---

## File Locations

```
Project: /home/linuxpc/Desktop/groq cli custom/

Prompts:
  /iabuilder/prompts/__init__.py
  /iabuilder/prompts/base.py
  /iabuilder/prompts/variants.py

Providers:
  /iabuilder/providers/mistral.py
  /iabuilder/providers/together.py
  /iabuilder/providers/deepseek.py
  /iabuilder/providers/cohere.py
  /iabuilder/providers/__init__.py (updated)

Documentation:
  /SPRINT_4_SUMMARY.md
  /QUICK_REFERENCE.md (this file)
```

---

*Quick Reference for Sprint 4.4 & 4.6*
*Last Updated: December 26, 2024*
