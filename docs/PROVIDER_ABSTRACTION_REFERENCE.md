# Provider Abstraction System - Quick Reference

## Directory Structure

```
iabuilder/
├── providers/              # Provider implementations
│   ├── __init__.py        # Provider exports
│   ├── base.py            # Abstract base class (ModelProvider)
│   └── groq.py            # Groq implementation (GroqProvider)
└── config/                 # Configuration and detection
    ├── __init__.py        # Config exports
    ├── config.py          # Configuration management
    └── api_detector.py    # API format detection
```

## Key Classes

### ModelProvider (Abstract Base Class)
**Location**: `iabuilder/providers/base.py`

**Purpose**: Defines the interface all LLM providers must implement

**Required Properties**:
- `provider_name` - Returns provider identifier (e.g., "groq")

**Required Methods**:
```python
async def list_available_models() -> List[Dict[str, Any]]
def get_fallback_models() -> List[Dict[str, Any]]
async def chat_completion(messages, model, tools, ...) -> Any
def validate_api_key() -> bool
def categorize_models() -> Dict[str, List[str]]
def supports_function_calling(model) -> bool
```

**Utility Methods**:
- `switch_model(model)` - Change current model
- `get_current_model()` - Get current model

### GroqProvider
**Location**: `iabuilder/providers/groq.py`

**Purpose**: Groq API implementation of ModelProvider

**Usage**:
```python
from iabuilder.providers import GroqProvider

provider = GroqProvider(
    api_key="gsk_your_key",
    model="llama-3.3-70b-versatile"
)

# Get models
models = provider.get_fallback_models()

# Check capabilities
can_call_functions = provider.supports_function_calling()
```

### APIDetector
**Location**: `iabuilder/config/api_detector.py`

**Purpose**: Detect API provider from keys, URLs, and configurations

**Key Methods**:
```python
# Detect provider from API key
format = APIDetector.detect_from_api_key("gsk_...")
# Returns: APIFormat.GROQ

# Detect from base URL
format = APIDetector.detect_from_base_url("https://api.groq.com")

# Combined detection
format = APIDetector.detect_format(
    api_key="gsk_...",
    base_url="https://api.groq.com"
)

# Get provider capabilities
caps = APIDetector.get_capabilities(APIFormat.GROQ)
print(caps.supports_streaming)  # True
print(caps.max_context_length)  # 128000

# Validate configuration
result = APIDetector.validate_configuration(
    api_key="gsk_test",
    expected_format=APIFormat.GROQ
)
```

### APIFormat (Enum)
**Supported Formats**:
- `APIFormat.GROQ` - Groq API
- `APIFormat.OPENAI` - OpenAI API
- `APIFormat.ANTHROPIC` - Anthropic (Claude) API
- `APIFormat.GOOGLE` - Google AI (Gemini) API
- `APIFormat.AZURE` - Azure OpenAI Service
- `APIFormat.UNKNOWN` - Unknown/undetected format

### APICapabilities (Dataclass)
**Fields**:
```python
format: APIFormat
supports_streaming: bool
supports_function_calling: bool
supports_vision: bool
supports_embeddings: bool
max_context_length: int
requires_system_message: bool
message_format: str  # "openai", "anthropic", "google"
```

## Exception Hierarchy

```
Exception
└── ProviderError (base)
    ├── AuthenticationError
    ├── ModelNotFoundError
    ├── RateLimitError
    └── APIError
```

**Usage**:
```python
from iabuilder.providers import (
    ProviderError,
    AuthenticationError,
    RateLimitError
)

try:
    response = await provider.chat_completion(messages)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError:
    print("Rate limited, please wait")
except ProviderError as e:
    print(f"Provider error: {e}")
```

## API Key Patterns

| Provider   | Key Pattern                      | Example Prefix      |
|------------|----------------------------------|---------------------|
| Groq       | `gsk_`                          | gsk_abc123...       |
| OpenAI     | `sk-` + 20+ alphanumeric        | sk-proj123...       |
| Anthropic  | `sk-ant-`                       | sk-ant-api03...     |
| Google     | `AIza` + 33+ chars              | AIzaSyAbc123...     |
| Azure      | 32-char hex                     | a1b2c3d4e5f6...     |

## Model Information Format

All providers return models in this format:
```python
{
    "id": "llama-3.3-70b-versatile",
    "name": "LLaMA 3.3 70B Versatile",
    "context_length": 128000,
    "supports_function_calling": True,
    "description": "Meta's latest LLaMA model"
}
```

## Provider Categories

Models are categorized as:
- `llm` - Large Language Models
- `whisper` - Speech recognition
- `tts` - Text-to-Speech
- `moderation` - Content moderation
- `vision` - Vision models
- `embedding` - Embedding models
- `other` - Uncategorized

## Testing

**Run tests**:
```bash
cd "/home/linuxpc/Desktop/groq cli custom"
./venv/bin/python3 test_provider_abstraction.py
```

**Expected output**: 5/5 tests passed

## Common Use Cases

### 1. Detect Provider from API Key
```python
from iabuilder.config import APIDetector

api_key = input("Enter API key: ")
provider_type = APIDetector.detect_from_api_key(api_key)

if provider_type == APIFormat.GROQ:
    print("Groq API detected")
elif provider_type == APIFormat.OPENAI:
    print("OpenAI API detected")
```

### 2. Get Provider Capabilities
```python
from iabuilder.config import APIDetector, APIFormat

caps = APIDetector.get_capabilities(APIFormat.GROQ)

if caps.supports_function_calling:
    print("This provider supports function calling")

print(f"Max context: {caps.max_context_length} tokens")
```

### 3. Validate API Configuration
```python
from iabuilder.config import APIDetector, APIFormat

result = APIDetector.validate_configuration(
    api_key="gsk_test123",
    base_url="https://api.groq.com",
    expected_format=APIFormat.GROQ
)

if not result['valid']:
    print("Configuration issues:")
    for issue in result['issues']:
        print(f"  - {issue}")
    for warning in result['warnings']:
        print(f"  ! {warning}")
```

### 4. Get Provider Information
```python
from iabuilder.config import APIDetector, APIFormat

info = APIDetector.get_provider_info(APIFormat.GROQ)
print(f"Provider: {info['name']}")
print(f"Website: {info['website']}")
print(f"Documentation: {info['docs']}")
print(f"Sign up: {info['signup']}")
```

### 5. Create Provider Instance
```python
from iabuilder.providers import GroqProvider

provider = GroqProvider(
    api_key="gsk_your_key_here",
    model="llama-3.3-70b-versatile"
)

# Validate key
if provider.validate_api_key():
    print("API key is valid")

# Get models
models = provider.get_fallback_models()
print(f"Available models: {len(models)}")

# Check function calling
if provider.supports_function_calling():
    print("Current model supports function calling")
```

## Adding New Providers

To add a new provider (e.g., OpenAI):

1. **Create provider file**: `iabuilder/providers/openai.py`
2. **Implement ModelProvider**:
```python
from .base import ModelProvider

class OpenAIProvider(ModelProvider):
    @property
    def provider_name(self) -> str:
        return "openai"

    async def list_available_models(self):
        # Implementation
        pass

    # ... implement all abstract methods
```

3. **Update exports**: Add to `iabuilder/providers/__init__.py`
```python
from .openai import OpenAIProvider

__all__ = [..., "OpenAIProvider"]
```

4. **Add to detector**: Update `api_detector.py` patterns
5. **Add tests**: Extend `test_provider_abstraction.py`

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `providers/base.py` | 188 | Abstract base class and exceptions |
| `providers/groq.py` | 364 | Groq provider implementation |
| `config/api_detector.py` | 368 | API format detection and validation |
| `test_provider_abstraction.py` | 280 | Comprehensive test suite |

## Design Principles

1. **Single Responsibility**: Each provider handles only its API
2. **Open/Closed**: Easy to extend, no modification needed
3. **Liskov Substitution**: All providers interchangeable
4. **Interface Segregation**: Clean, minimal interface
5. **Dependency Inversion**: Depend on abstractions, not implementations

## Future Providers

Ready to implement:
- ✓ Groq (implemented)
- ⏳ OpenAI (planned - Sprint 4.2)
- ⏳ Anthropic (planned - Sprint 4.3)
- ⏳ Google (planned - Sprint 4.5)
- ⏳ Azure (planned - Sprint 4.5)

---

**Version**: 1.0.0
**Sprint**: 4.1
**Date**: 2025-12-26
**Status**: Production Ready
