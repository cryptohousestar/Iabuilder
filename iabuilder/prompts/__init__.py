"""Prompt management for different model families.

This package provides intelligent prompt variants tailored for different
model families to optimize function calling and general performance.
"""

from .base import BasePromptTemplate, StrictnessLevel
from .variants import PromptVariantManager, detect_model_family

__all__ = [
    "BasePromptTemplate",
    "StrictnessLevel",
    "PromptVariantManager",
    "detect_model_family",
]
