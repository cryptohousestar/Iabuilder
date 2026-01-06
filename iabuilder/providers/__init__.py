"""Provider abstraction for multi-LLM support.

This package provides a unified interface for different LLM providers
including Groq, OpenAI, Anthropic, Google, OpenRouter, Mistral, Together,
DeepSeek, Cohere, and others.
"""

from .base import (
    APIError,
    AuthenticationError,
    ModelNotFoundError,
    ModelProvider,
    ProviderError,
    RateLimitError,
)
from .groq import GroqProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .google import GoogleProvider
from .openrouter import OpenRouterProvider
from .aiml import AIMLProvider
from .mistral import MistralProvider
from .together import TogetherProvider
from .deepseek import DeepSeekProvider
from .cohere import CohereProvider

__all__ = [
    # Base classes and errors
    "ModelProvider",
    "ProviderError",
    "AuthenticationError",
    "ModelNotFoundError",
    "RateLimitError",
    "APIError",
    # Provider implementations
    "GroqProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "OpenRouterProvider",
    "AIMLProvider",
    "MistralProvider",
    "TogetherProvider",
    "DeepSeekProvider",
    "CohereProvider",
]
