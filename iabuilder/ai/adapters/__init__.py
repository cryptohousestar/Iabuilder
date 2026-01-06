"""Model family adapters for IABuilder.

This module provides adapters for different LLM families to handle
their specific behaviors for tool calling and response parsing.
"""

from .registry import get_adapter_for_model, detect_family, FAMILY_PATTERNS
from .base import AbstractAdapter, ToolCall, ParsedResponse

__all__ = [
    "get_adapter_for_model",
    "detect_family",
    "FAMILY_PATTERNS",
    "AbstractAdapter",
    "ToolCall",
    "ParsedResponse",
]
