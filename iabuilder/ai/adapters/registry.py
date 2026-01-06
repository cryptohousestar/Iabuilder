"""Adapter registry with family detection for model adapters."""

from typing import Dict, List, Optional, Type
from .base import AbstractAdapter


# Pattern-based family detection
# Add new patterns here when new models are released
FAMILY_PATTERNS: Dict[str, List[str]] = {
    "openai": [
        "gpt-4", "gpt-3.5", "gpt-4o", "gpt-4-turbo",
        "o1-", "o1o-", "o3-",  # Reasoning models
        "chatgpt", "openai/gpt",
    ],
    "anthropic": [
        "claude", "anthropic/claude",
    ],
    "google": [
        "gemini", "google/gemini", "palm", "bard",
        "gemini-1", "gemini-2", "gemini-3",  # Future versions
    ],
    "meta": [
        "llama", "meta-llama", "meta/llama",
        "llama-2", "llama-3", "llama-4",  # Future versions
    ],
    "qwen": [
        "qwen", "qwen2", "qwen-2", "alibaba/qwen",
    ],
    "mistral": [
        "mistral", "mixtral", "mistralai", "codestral",
        "ministral", "pixtral",
    ],
    "deepseek": [
        "deepseek",
    ],
    "cohere": [
        "command", "cohere", "command-r",
    ],
}

# Support levels for display
SUPPORT_LEVELS = {
    "optimized": "Optimizado",
    "compatible": "Compatible",
    "experimental": "Experimental",
}

# Cache for adapter instances
_adapter_cache: Dict[str, AbstractAdapter] = {}


def detect_family(model_name: str) -> str:
    """Detect the model family from the model name.

    Uses pattern matching to identify which family a model belongs to.
    Returns 'generic' if no match is found.

    Args:
        model_name: The model identifier (e.g., "google/gemini-2.0-flash-001")

    Returns:
        Family name (e.g., "google", "openai", "meta", "generic")
    """
    model_lower = model_name.lower()

    for family, patterns in FAMILY_PATTERNS.items():
        for pattern in patterns:
            if pattern in model_lower:
                return family

    return "generic"


def get_adapter_class(family: str) -> Type[AbstractAdapter]:
    """Get the adapter class for a model family.

    Args:
        family: Family name (e.g., "openai", "google")

    Returns:
        Adapter class for the family
    """
    # Import adapters lazily to avoid circular imports
    if family == "openai":
        from .openai_adapter import OpenAIAdapter
        return OpenAIAdapter
    elif family == "anthropic":
        from .anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter
    elif family == "google":
        from .google_adapter import GoogleAdapter
        return GoogleAdapter
    elif family == "meta":
        from .meta_adapter import MetaAdapter
        return MetaAdapter
    elif family == "qwen":
        from .qwen_adapter import QwenAdapter
        return QwenAdapter
    elif family == "mistral":
        from .mistral_adapter import MistralAdapter
        return MistralAdapter
    elif family == "deepseek":
        from .deepseek_adapter import DeepSeekAdapter
        return DeepSeekAdapter
    elif family == "cohere":
        from .cohere_adapter import CohereAdapter
        return CohereAdapter
    else:
        from .generic_adapter import GenericAdapter
        return GenericAdapter


def get_adapter_for_model(
    model_name: str,
    use_cache: bool = True
) -> AbstractAdapter:
    """Get an adapter instance for a specific model.

    This is the main entry point for getting adapters. It:
    1. Detects the model family
    2. Gets the appropriate adapter class
    3. Creates and caches an instance

    Args:
        model_name: The model identifier
        use_cache: Whether to use cached adapters (default True)

    Returns:
        AbstractAdapter instance for the model
    """
    if use_cache and model_name in _adapter_cache:
        return _adapter_cache[model_name]

    family = detect_family(model_name)
    adapter_class = get_adapter_class(family)
    adapter = adapter_class(model_name)

    if use_cache:
        _adapter_cache[model_name] = adapter

    return adapter


def clear_adapter_cache():
    """Clear the adapter cache."""
    global _adapter_cache
    _adapter_cache = {}


def get_all_families() -> List[str]:
    """Get list of all supported model families.

    Returns:
        List of family names
    """
    return list(FAMILY_PATTERNS.keys()) + ["generic"]


def get_family_info(family: str) -> Dict:
    """Get information about a model family.

    Args:
        family: Family name

    Returns:
        Dictionary with family information
    """
    adapter_class = get_adapter_class(family)

    return {
        "family": family,
        "patterns": FAMILY_PATTERNS.get(family, []),
        "support_level": adapter_class.support_level if hasattr(adapter_class, 'support_level') else "experimental",
        "supports_tools": adapter_class.supports_tools if hasattr(adapter_class, 'supports_tools') else True,
    }


def get_support_emoji(support_level: str) -> str:
    """Get emoji for support level.

    Args:
        support_level: Support level string

    Returns:
        Emoji representation
    """
    emojis = {
        "optimized": "⭐",
        "compatible": "✓",
        "experimental": "⚠️",
    }
    return emojis.get(support_level, "?")
