"""Model-specific rate limits for Groq API.

Based on official Groq documentation: https://console.groq.com/docs/rate-limits
Updated: 2025-12-22
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelLimits:
    """Rate limits for a specific model."""
    rpm: int  # Requests per minute
    tpm: int  # Tokens per minute
    rpd: Optional[int] = None  # Requests per day
    tpd: Optional[int] = None  # Tokens per day
    tier: str = "free"  # "free" or "paid"


# FREE TIER LIMITS
# Being VERY conservative: using 70% of actual limits to avoid hitting edges
FREE_TIER_LIMITS = {
    # Llama Models
    "llama-3.3-70b-versatile": ModelLimits(
        rpm=20,      # Actual: 30, using 20 to be safe
        tpm=8_000,   # Actual: 12K, using 8K to be safe
        rpd=700,     # Actual: 1K, using 700 to be safe
        tpd=70_000,  # Actual: 100K, using 70K to be safe
        tier="free"
    ),
    "llama-3.1-8b-instant": ModelLimits(
        rpm=20,      # Actual: 30, using 20
        tpm=4_000,   # Actual: 6K, using 4K
        rpd=10_000,  # Actual: 14.4K, using 10K
        tpd=350_000, # Actual: 500K, using 350K
        tier="free"
    ),
    "meta-llama/llama-4-maverick-17b-128e-instruct": ModelLimits(
        rpm=20,
        tpm=4_000,
        rpd=700,
        tpd=350_000,
        tier="free"
    ),
    "meta-llama/llama-4-scout-17b-16e-instruct": ModelLimits(
        rpm=20,
        tpm=20_000,  # Actual: 30K, using 20K
        rpd=700,
        tpd=350_000,
        tier="free"
    ),

    # Compound Models (High TPM)
    "groq/compound": ModelLimits(
        rpm=20,
        tpm=50_000,  # Actual: 70K, using 50K to be safe
        rpd=175,     # Actual: 250, using 175
        tier="free"
    ),
    "groq/compound-mini": ModelLimits(
        rpm=20,
        tpm=50_000,
        rpd=175,
        tier="free"
    ),

    # Qwen Models
    "qwen/qwen3-32b": ModelLimits(
        rpm=40,      # Actual: 60, using 40
        tpm=4_000,   # Actual: 6K, using 4K
        rpd=700,
        tpd=350_000,
        tier="free"
    ),

    # OpenAI OSS Models
    "openai/gpt-oss-120b": ModelLimits(
        rpm=20,
        tpm=5_600,   # Actual: 8K, using 5.6K
        rpd=700,
        tpd=140_000,
        tier="free"
    ),
    "openai/gpt-oss-20b": ModelLimits(
        rpm=20,
        tpm=5_600,
        rpd=700,
        tpd=140_000,
        tier="free"
    ),

    # Moonshotai Kimi Models
    "moonshotai/kimi-k2-instruct": ModelLimits(
        rpm=40,      # Actual: 60, using 40
        tpm=7_000,   # Actual: 10K, using 7K
        rpd=700,
        tpd=210_000,
        tier="free"
    ),
    "moonshotai/kimi-k2-instruct-0905": ModelLimits(
        rpm=40,
        tpm=7_000,
        rpd=700,
        tpd=210_000,
        tier="free"
    ),

    # Guard Models
    "meta-llama/llama-guard-4-12b": ModelLimits(
        rpm=20,
        tpm=10_000,  # Actual: 15K, using 10K
        rpd=10_000,
        tpd=350_000,
        tier="free"
    ),
    "meta-llama/llama-prompt-guard-2-22m": ModelLimits(
        rpm=20,
        tpm=10_000,
        rpd=10_000,
        tpd=350_000,
        tier="free"
    ),
    "meta-llama/llama-prompt-guard-2-86m": ModelLimits(
        rpm=20,
        tpm=10_000,
        rpd=10_000,
        tpd=350_000,
        tier="free"
    ),

    # Allam Models
    "allam-2-7b": ModelLimits(
        rpm=20,
        tpm=4_000,
        rpd=5_000,
        tpd=350_000,
        tier="free"
    ),

    # Whisper Models (Audio)
    "whisper-large-v3": ModelLimits(
        rpm=14,      # Actual: 20, using 14
        tpm=0,       # Audio models don't use TPM
        rpd=1_400,
        tier="free"
    ),
    "whisper-large-v3-turbo": ModelLimits(
        rpm=14,
        tpm=0,
        rpd=1_400,
        tier="free"
    ),

    # Legacy/Compatibility Models
    "llama-3.2-90b-text-preview": ModelLimits(
        rpm=20,
        tpm=6_000,
        rpd=700,
        tpd=100_000,
        tier="free"
    ),
    "llama-3.2-11b-text-preview": ModelLimits(
        rpm=20,
        tpm=6_000,
        rpd=5_000,
        tpd=250_000,
        tier="free"
    ),
    "llama-3.1-70b-versatile": ModelLimits(
        rpm=20,
        tpm=4_000,
        rpd=700,
        tpd=70_000,
        tier="free"
    ),
    "mixtral-8x7b-32768": ModelLimits(
        rpm=20,
        tpm=3_500,  # Actual: 5K, being very conservative
        rpd=700,
        tpd=70_000,
        tier="free"
    ),
    "gemma-7b-it": ModelLimits(
        rpm=20,
        tpm=4_000,
        rpd=5_000,
        tpd=250_000,
        tier="free"
    ),
    "gemma2-9b-it": ModelLimits(
        rpm=20,
        tpm=10_000,
        rpd=5_000,
        tpd=350_000,
        tier="free"
    ),
}


# PAID/DEVELOPER TIER LIMITS
# Still conservative, using ~80% of actual limits
PAID_TIER_LIMITS = {
    "llama-3.3-70b-versatile": ModelLimits(
        rpm=800,      # Actual: 1K, using 800
        tpm=240_000,  # Actual: 300K, using 240K
        rpd=400_000,  # Actual: 500K, using 400K
        tier="paid"
    ),
    "llama-3.1-8b-instant": ModelLimits(
        rpm=800,
        tpm=200_000,  # Actual: 250K, using 200K
        rpd=400_000,
        tier="paid"
    ),
    "openai/gpt-oss-20b": ModelLimits(
        rpm=800,
        tpm=200_000,
        rpd=400_000,
        tier="paid"
    ),
    "whisper-large-v3-turbo": ModelLimits(
        rpm=320,      # Actual: 400, using 320
        tpm=0,
        rpd=160_000,  # Actual: 200K, using 160K
        tier="paid"
    ),
}


# OPENROUTER LIMITS (much more generous)
# OpenRouter doesn't have strict TPM limits for most models
OPENROUTER_LIMITS = {
    # Free tier models on OpenRouter are generally generous
    "default": ModelLimits(
        rpm=60,        # OpenRouter allows ~60 RPM for free tier
        tpm=100_000,   # No strict TPM limit, using 100K as safe default
        rpd=1000,      # Reasonable daily limit
        tpd=1_000_000, # Very generous
        tier="free"
    ),
    # Specific free models that might have lower limits
    "free": ModelLimits(
        rpm=30,        # Conservative for free models
        tpm=50_000,    # Still generous
        rpd=500,
        tpd=500_000,
        tier="free"
    ),
}

# DEFAULT FALLBACK for unknown providers (conservative)
DEFAULT_LIMITS = ModelLimits(
    rpm=30,       # Increased from 15
    tpm=20_000,   # Increased from 3K
    rpd=500,
    tpd=100_000,
    tier="free"
)


def get_model_limits(model_name: str, tier: str = "free", provider: str = "groq") -> ModelLimits:
    """Get rate limits for a specific model.

    Args:
        model_name: Name of the model
        tier: "free" or "paid"
        provider: Provider name (groq, openrouter, openai, etc.)

    Returns:
        ModelLimits object with rate limits for this model
    """
    provider = provider.lower() if provider else "groq"

    # OpenRouter has more generous limits
    if provider == "openrouter":
        # Check if it's a free model (contains :free suffix)
        if ":free" in model_name.lower():
            return OPENROUTER_LIMITS["free"]
        return OPENROUTER_LIMITS["default"]

    # For non-Groq providers, use generous defaults
    if provider not in ["groq"]:
        return DEFAULT_LIMITS

    # Groq-specific limits
    limits_dict = PAID_TIER_LIMITS if tier == "paid" else FREE_TIER_LIMITS

    # Try exact match first
    if model_name in limits_dict:
        return limits_dict[model_name]

    # Try partial match (for aliases)
    for key in limits_dict:
        if model_name in key or key in model_name:
            return limits_dict[key]

    # Fallback to default limits
    return DEFAULT_LIMITS


def is_audio_model(model_name: str) -> bool:
    """Check if model is an audio model (Whisper)."""
    return "whisper" in model_name.lower()


def is_vision_model(model_name: str) -> bool:
    """Check if model is a vision model."""
    return "vision" in model_name.lower() or "llava" in model_name.lower()


def get_recommended_buffer_tokens(model_name: str) -> int:
    """Get recommended buffer tokens for a model.

    Returns lower buffer for models with higher TPM limits.
    """
    limits = get_model_limits(model_name)

    if limits.tpm >= 50_000:  # High TPM models (compound)
        return 2_000
    elif limits.tpm >= 10_000:  # Medium-high TPM
        return 1_000
    else:  # Lower TPM models
        return 500


def print_model_info(model_name: str, tier: str = "free"):
    """Print formatted information about a model's limits."""
    limits = get_model_limits(model_name, tier)

    print(f"\n📊 Rate Limits for {model_name} ({tier} tier):")
    print(f"   RPM (Requests/min): {limits.rpm:,}")
    print(f"   TPM (Tokens/min):   {limits.tpm:,}")
    if limits.rpd:
        print(f"   RPD (Requests/day): {limits.rpd:,}")
    if limits.tpd:
        print(f"   TPD (Tokens/day):   {limits.tpd:,}")
    print()
