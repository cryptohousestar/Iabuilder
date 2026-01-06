"""Comprehensive model capabilities database for all supported providers.

This module contains detailed information about models from:
- Groq (free and paid tiers)
- OpenRouter (400+ models gateway)
- Anthropic (Claude family)
- OpenAI (GPT family)
- Google (Gemini family)

Each model entry includes:
- Context window size
- Function/tool calling support
- Speed (tokens/sec where available)
- Pricing tier (free/paid)
- Special capabilities (vision, audio, reasoning, etc.)
- Recommended use cases
- Star rating for development tasks (1-5)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class PricingTier(Enum):
    """Model pricing tier."""
    FREE = "free"
    PAID = "paid"
    PREMIUM = "premium"  # High-cost models


class ModelCategory(Enum):
    """Model category/type."""
    LLM = "llm"  # Text generation
    VISION = "vision"  # Vision + text
    MULTIMODAL = "multimodal"  # Multiple modalities
    REASONING = "reasoning"  # Enhanced reasoning (o1, thinking)
    CODING = "coding"  # Specialized for code
    EMBEDDING = "embedding"  # Text embeddings
    AUDIO = "audio"  # Speech/audio processing
    IMAGE_GEN = "image_gen"  # Image generation


@dataclass
class ModelCapability:
    """Detailed model capability information."""

    # Basic info
    id: str
    name: str
    provider: str

    # Context and limits
    context_window: int
    max_output_tokens: int = 0

    # Capabilities
    supports_tools: bool = True
    supports_parallel_tools: bool = False
    supports_vision: bool = False
    supports_audio: bool = False
    supports_streaming: bool = True
    supports_json_mode: bool = False

    # Performance
    speed_tps: Optional[int] = None  # Tokens per second
    latency_class: str = "medium"  # low, medium, high

    # Pricing
    tier: PricingTier = PricingTier.PAID
    input_cost_per_million: Optional[float] = None
    output_cost_per_million: Optional[float] = None

    # Classification
    category: ModelCategory = ModelCategory.LLM
    specializations: List[str] = field(default_factory=list)

    # Recommendations
    dev_rating: int = 3  # 1-5 stars for development tasks
    best_for: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    # Notes
    notes: str = ""


# =============================================================================
# GROQ MODELS - Free Tier (High Speed)
# =============================================================================

GROQ_MODELS: Dict[str, ModelCapability] = {
    # Llama 4 Series (Latest)
    "meta-llama/llama-4-maverick-17b-128e-instruct": ModelCapability(
        id="meta-llama/llama-4-maverick-17b-128e-instruct",
        name="Llama 4 Maverick 17B",
        provider="groq",
        context_window=131072,
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        speed_tps=800,
        latency_class="low",
        tier=PricingTier.FREE,
        category=ModelCategory.MULTIMODAL,
        specializations=["coding", "reasoning", "agents"],
        dev_rating=5,
        best_for=["Development", "Code generation", "Complex tasks", "Agents"],
        notes="Latest Llama with excellent tool use and vision support"
    ),

    "meta-llama/llama-4-scout-17b-16e-instruct": ModelCapability(
        id="meta-llama/llama-4-scout-17b-16e-instruct",
        name="Llama 4 Scout 17B",
        provider="groq",
        context_window=131072,
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        speed_tps=1000,
        latency_class="low",
        tier=PricingTier.FREE,
        category=ModelCategory.MULTIMODAL,
        specializations=["fast-inference", "coding"],
        dev_rating=4,
        best_for=["Quick tasks", "Iterative development", "Code review"],
        notes="Faster variant of Llama 4 for quick iterations"
    ),

    # Llama 3.3 Series
    "llama-3.3-70b-versatile": ModelCapability(
        id="llama-3.3-70b-versatile",
        name="Llama 3.3 70B Versatile",
        provider="groq",
        context_window=131072,
        max_output_tokens=32768,
        supports_tools=True,
        supports_parallel_tools=True,
        speed_tps=275,
        latency_class="medium",
        tier=PricingTier.FREE,
        category=ModelCategory.LLM,
        specializations=["general", "coding", "analysis"],
        dev_rating=5,
        best_for=["Complex coding", "Analysis", "Documentation"],
        notes="Excellent balance of capability and speed"
    ),

    "llama-3.3-70b-specdec": ModelCapability(
        id="llama-3.3-70b-specdec",
        name="Llama 3.3 70B SpecDec",
        provider="groq",
        context_window=8192,
        max_output_tokens=8192,
        supports_tools=True,
        speed_tps=1200,
        latency_class="low",
        tier=PricingTier.FREE,
        category=ModelCategory.LLM,
        specializations=["fast-inference"],
        dev_rating=4,
        best_for=["Quick responses", "Simple tasks"],
        limitations=["Small context window"],
        notes="Speculative decoding for ultra-fast inference"
    ),

    # Llama 3.1 Series
    "llama-3.1-8b-instant": ModelCapability(
        id="llama-3.1-8b-instant",
        name="Llama 3.1 8B Instant",
        provider="groq",
        context_window=131072,
        max_output_tokens=8192,
        supports_tools=True,
        speed_tps=1300,
        latency_class="low",
        tier=PricingTier.FREE,
        category=ModelCategory.LLM,
        specializations=["fast-inference", "simple-tasks"],
        dev_rating=3,
        best_for=["Quick queries", "Simple coding", "Chat"],
        limitations=["Less capable for complex tasks"],
        notes="Fast and lightweight, good for simple tasks"
    ),

    # Qwen Series
    "qwen/qwen3-32b": ModelCapability(
        id="qwen/qwen3-32b",
        name="Qwen 3 32B",
        provider="groq",
        context_window=131072,
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        speed_tps=400,
        latency_class="medium",
        tier=PricingTier.FREE,
        category=ModelCategory.LLM,
        specializations=["multilingual", "coding", "reasoning"],
        dev_rating=4,
        best_for=["Multilingual tasks", "Coding", "Reasoning"],
        notes="Excellent multilingual support, strong at coding"
    ),

    # Kimi Series (Large Context)
    "moonshotai/kimi-k2-instruct": ModelCapability(
        id="moonshotai/kimi-k2-instruct",
        name="Kimi K2 Instruct",
        provider="groq",
        context_window=262144,  # 256K!
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        speed_tps=200,
        latency_class="medium",
        tier=PricingTier.FREE,
        category=ModelCategory.LLM,
        specializations=["long-context", "analysis"],
        dev_rating=4,
        best_for=["Large codebases", "Long documents", "Analysis"],
        notes="Largest context window on Groq - 256K tokens"
    ),

    # Compound AI (Beta)
    "compound-beta": ModelCapability(
        id="compound-beta",
        name="Compound AI Beta",
        provider="groq",
        context_window=131072,
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        speed_tps=300,
        latency_class="medium",
        tier=PricingTier.FREE,
        category=ModelCategory.REASONING,
        specializations=["reasoning", "web-search", "code-execution"],
        dev_rating=4,
        best_for=["Complex reasoning", "Research", "Multi-step tasks"],
        notes="Built-in web search and code execution"
    ),

    "compound-beta-mini": ModelCapability(
        id="compound-beta-mini",
        name="Compound AI Beta Mini",
        provider="groq",
        context_window=131072,
        max_output_tokens=8192,
        supports_tools=True,
        speed_tps=500,
        latency_class="low",
        tier=PricingTier.FREE,
        category=ModelCategory.REASONING,
        specializations=["reasoning", "fast"],
        dev_rating=3,
        best_for=["Quick reasoning tasks"],
        notes="Lighter version of Compound AI"
    ),

    # Gemma Series
    "gemma2-9b-it": ModelCapability(
        id="gemma2-9b-it",
        name="Gemma 2 9B IT",
        provider="groq",
        context_window=8192,
        max_output_tokens=4096,
        supports_tools=True,
        speed_tps=800,
        latency_class="low",
        tier=PricingTier.FREE,
        category=ModelCategory.LLM,
        specializations=["efficient", "chat"],
        dev_rating=3,
        best_for=["Simple tasks", "Conversation"],
        limitations=["Small context", "Less capable"],
        notes="Google's efficient open model"
    ),

    # Mistral Series
    "mistral-saba-24b": ModelCapability(
        id="mistral-saba-24b",
        name="Mistral Saba 24B",
        provider="groq",
        context_window=32768,
        max_output_tokens=8192,
        supports_tools=True,
        speed_tps=500,
        latency_class="low",
        tier=PricingTier.FREE,
        category=ModelCategory.LLM,
        specializations=["multilingual", "middle-east-asian"],
        dev_rating=3,
        best_for=["Middle Eastern/Asian languages"],
        notes="Optimized for Arabic, Hebrew, Persian, etc."
    ),

    # DeepSeek Series
    "deepseek-r1-distill-llama-70b": ModelCapability(
        id="deepseek-r1-distill-llama-70b",
        name="DeepSeek R1 Distill 70B",
        provider="groq",
        context_window=131072,
        max_output_tokens=16384,
        supports_tools=True,
        speed_tps=250,
        latency_class="medium",
        tier=PricingTier.FREE,
        category=ModelCategory.REASONING,
        specializations=["reasoning", "math", "coding"],
        dev_rating=4,
        best_for=["Complex reasoning", "Math", "Code analysis"],
        notes="Reasoning-focused distillation of DeepSeek R1"
    ),

    # GPT-OSS Series (OpenAI Compatible)
    "openai/gpt-oss-4o-mini": ModelCapability(
        id="openai/gpt-oss-4o-mini",
        name="GPT-OSS 4o Mini",
        provider="groq",
        context_window=131072,
        max_output_tokens=16384,
        supports_tools=True,
        supports_parallel_tools=True,
        speed_tps=350,
        latency_class="medium",
        tier=PricingTier.FREE,
        category=ModelCategory.LLM,
        specializations=["openai-compatible", "general"],
        dev_rating=4,
        best_for=["General tasks", "OpenAI API compatibility"],
        notes="Open-source GPT-4o mini compatible model"
    ),

    # Audio Models (No tool support)
    "whisper-large-v3": ModelCapability(
        id="whisper-large-v3",
        name="Whisper Large V3",
        provider="groq",
        context_window=0,
        supports_tools=False,
        supports_streaming=False,
        supports_audio=True,
        tier=PricingTier.FREE,
        category=ModelCategory.AUDIO,
        specializations=["transcription", "translation"],
        dev_rating=5,
        best_for=["Audio transcription", "Speech-to-text"],
        notes="Best-in-class audio transcription"
    ),

    "whisper-large-v3-turbo": ModelCapability(
        id="whisper-large-v3-turbo",
        name="Whisper Large V3 Turbo",
        provider="groq",
        context_window=0,
        supports_tools=False,
        supports_streaming=False,
        supports_audio=True,
        speed_tps=2000,
        tier=PricingTier.FREE,
        category=ModelCategory.AUDIO,
        specializations=["transcription", "fast"],
        dev_rating=5,
        best_for=["Fast audio transcription"],
        notes="Faster variant of Whisper"
    ),

    # TTS Models
    "playai-tts": ModelCapability(
        id="playai-tts",
        name="PlayAI TTS",
        provider="groq",
        context_window=0,
        supports_tools=False,
        supports_streaming=True,
        tier=PricingTier.FREE,
        category=ModelCategory.AUDIO,
        specializations=["text-to-speech"],
        dev_rating=4,
        best_for=["Voice generation", "TTS"],
        notes="High-quality text-to-speech"
    ),

    "playai-tts-arabic": ModelCapability(
        id="playai-tts-arabic",
        name="PlayAI TTS Arabic",
        provider="groq",
        context_window=0,
        supports_tools=False,
        supports_streaming=True,
        tier=PricingTier.FREE,
        category=ModelCategory.AUDIO,
        specializations=["text-to-speech", "arabic"],
        dev_rating=4,
        best_for=["Arabic voice generation"],
        notes="Arabic-optimized TTS"
    ),
}


# =============================================================================
# ANTHROPIC MODELS - Claude Family
# =============================================================================

ANTHROPIC_MODELS: Dict[str, ModelCapability] = {
    # Claude 4.5 Series (Latest)
    "claude-sonnet-4-5-20250514": ModelCapability(
        id="claude-sonnet-4-5-20250514",
        name="Claude Sonnet 4.5",
        provider="anthropic",
        context_window=200000,  # 200K standard, 1M with beta header
        max_output_tokens=16384,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_json_mode=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        input_cost_per_million=3.0,
        output_cost_per_million=15.0,
        category=ModelCategory.MULTIMODAL,
        specializations=["coding", "agents", "analysis", "reasoning"],
        dev_rating=5,
        best_for=["Complex coding", "Agents", "Multi-step tasks", "Analysis"],
        notes="Best balance of intelligence, speed, and cost. Supports 1M context with beta header."
    ),

    "claude-opus-4-20250514": ModelCapability(
        id="claude-opus-4-20250514",
        name="Claude Opus 4",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=32768,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_json_mode=True,
        latency_class="high",
        tier=PricingTier.PREMIUM,
        input_cost_per_million=15.0,
        output_cost_per_million=75.0,
        category=ModelCategory.MULTIMODAL,
        specializations=["complex-reasoning", "research", "writing"],
        dev_rating=5,
        best_for=["Most complex tasks", "Research", "Long-form content"],
        notes="Most capable Claude model, highest quality outputs"
    ),

    "claude-haiku-4-5-20250514": ModelCapability(
        id="claude-haiku-4-5-20250514",
        name="Claude Haiku 4.5",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_json_mode=True,
        latency_class="low",
        tier=PricingTier.PAID,
        input_cost_per_million=0.80,
        output_cost_per_million=4.0,
        category=ModelCategory.MULTIMODAL,
        specializations=["fast", "cost-effective", "chat"],
        dev_rating=4,
        best_for=["Quick responses", "High-volume tasks", "Chat"],
        notes="Fastest Claude, excellent for cost-sensitive applications"
    ),

    # Aliases for latest versions
    "claude-3-5-sonnet-latest": ModelCapability(
        id="claude-3-5-sonnet-latest",
        name="Claude 3.5 Sonnet (Latest)",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_json_mode=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        input_cost_per_million=3.0,
        output_cost_per_million=15.0,
        category=ModelCategory.MULTIMODAL,
        specializations=["coding", "analysis"],
        dev_rating=5,
        best_for=["Development", "Analysis", "General tasks"],
        notes="Previous generation, still excellent"
    ),
}


# =============================================================================
# OPENAI MODELS - GPT Family
# =============================================================================

OPENAI_MODELS: Dict[str, ModelCapability] = {
    # GPT-4.1 Series (Latest, 1M context)
    "gpt-4.1": ModelCapability(
        id="gpt-4.1",
        name="GPT-4.1",
        provider="openai",
        context_window=1000000,  # 1M tokens!
        max_output_tokens=32768,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_json_mode=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        input_cost_per_million=2.0,
        output_cost_per_million=8.0,
        category=ModelCategory.MULTIMODAL,
        specializations=["coding", "instruction-following", "long-context"],
        dev_rating=5,
        best_for=["Large codebases", "Complex instructions", "Long documents"],
        notes="Major improvements in coding, instruction following, and 1M context"
    ),

    "gpt-4.1-mini": ModelCapability(
        id="gpt-4.1-mini",
        name="GPT-4.1 Mini",
        provider="openai",
        context_window=1000000,
        max_output_tokens=16384,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_json_mode=True,
        latency_class="low",
        tier=PricingTier.PAID,
        input_cost_per_million=0.40,
        output_cost_per_million=1.60,
        category=ModelCategory.MULTIMODAL,
        specializations=["fast", "cost-effective", "coding"],
        dev_rating=4,
        best_for=["Cost-effective development", "Quick tasks"],
        notes="Fast and cheap with 1M context window"
    ),

    "gpt-4.1-nano": ModelCapability(
        id="gpt-4.1-nano",
        name="GPT-4.1 Nano",
        provider="openai",
        context_window=1000000,
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_json_mode=True,
        latency_class="low",
        tier=PricingTier.PAID,
        input_cost_per_million=0.10,
        output_cost_per_million=0.40,
        category=ModelCategory.LLM,
        specializations=["ultra-fast", "high-volume"],
        dev_rating=3,
        best_for=["Simple tasks", "High volume", "Real-time"],
        notes="Fastest and cheapest OpenAI model, still has 1M context"
    ),

    # GPT-4o Series
    "gpt-4o": ModelCapability(
        id="gpt-4o",
        name="GPT-4o",
        provider="openai",
        context_window=128000,
        max_output_tokens=16384,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_audio=True,
        supports_json_mode=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        input_cost_per_million=2.50,
        output_cost_per_million=10.0,
        category=ModelCategory.MULTIMODAL,
        specializations=["multimodal", "general"],
        dev_rating=5,
        best_for=["General development", "Vision tasks", "Audio"],
        notes="Excellent all-around model with multimodal support"
    ),

    "gpt-4o-mini": ModelCapability(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider="openai",
        context_window=128000,
        max_output_tokens=16384,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_json_mode=True,
        latency_class="low",
        tier=PricingTier.PAID,
        input_cost_per_million=0.15,
        output_cost_per_million=0.60,
        category=ModelCategory.MULTIMODAL,
        specializations=["fast", "cost-effective"],
        dev_rating=4,
        best_for=["Cost-effective tasks", "Quick development"],
        notes="Great value, strong function calling"
    ),

    # o1 Series (Reasoning)
    "o1": ModelCapability(
        id="o1",
        name="o1",
        provider="openai",
        context_window=200000,
        max_output_tokens=100000,
        supports_tools=True,
        supports_vision=True,
        supports_json_mode=True,
        latency_class="high",
        tier=PricingTier.PREMIUM,
        input_cost_per_million=15.0,
        output_cost_per_million=60.0,
        category=ModelCategory.REASONING,
        specializations=["complex-reasoning", "math", "science", "coding"],
        dev_rating=5,
        best_for=["Complex problems", "Math", "Science", "Algorithm design"],
        notes="Extended thinking for complex reasoning tasks"
    ),

    "o1-mini": ModelCapability(
        id="o1-mini",
        name="o1 Mini",
        provider="openai",
        context_window=128000,
        max_output_tokens=65536,
        supports_tools=True,
        supports_json_mode=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        input_cost_per_million=3.0,
        output_cost_per_million=12.0,
        category=ModelCategory.REASONING,
        specializations=["reasoning", "coding"],
        dev_rating=4,
        best_for=["Reasoning tasks", "STEM problems"],
        notes="Faster reasoning at lower cost"
    ),

    # GPT-4 Turbo (Legacy but still used)
    "gpt-4-turbo": ModelCapability(
        id="gpt-4-turbo",
        name="GPT-4 Turbo",
        provider="openai",
        context_window=128000,
        max_output_tokens=4096,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_json_mode=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        input_cost_per_million=10.0,
        output_cost_per_million=30.0,
        category=ModelCategory.MULTIMODAL,
        specializations=["general", "vision"],
        dev_rating=4,
        best_for=["Existing integrations"],
        limitations=["Lower output limit"],
        notes="Previous generation, consider upgrading to GPT-4.1"
    ),
}


# =============================================================================
# GOOGLE MODELS - Gemini Family
# =============================================================================

GOOGLE_MODELS: Dict[str, ModelCapability] = {
    # Gemini 2.5 Series (Latest Production)
    "gemini-2.5-pro-preview-06-05": ModelCapability(
        id="gemini-2.5-pro-preview-06-05",
        name="Gemini 2.5 Pro",
        provider="google",
        context_window=1000000,  # 1M tokens!
        max_output_tokens=65536,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_audio=True,
        supports_json_mode=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        input_cost_per_million=1.25,
        output_cost_per_million=10.0,
        category=ModelCategory.MULTIMODAL,
        specializations=["reasoning", "coding", "multimodal"],
        dev_rating=5,
        best_for=["Complex coding", "Long documents", "Multimodal"],
        notes="Enhanced thinking for complex reasoning, 1M context"
    ),

    "gemini-2.5-flash-preview-05-20": ModelCapability(
        id="gemini-2.5-flash-preview-05-20",
        name="Gemini 2.5 Flash",
        provider="google",
        context_window=1000000,
        max_output_tokens=65536,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_audio=True,
        supports_json_mode=True,
        latency_class="low",
        tier=PricingTier.PAID,
        input_cost_per_million=0.15,
        output_cost_per_million=0.60,
        category=ModelCategory.MULTIMODAL,
        specializations=["fast", "cost-effective", "agents"],
        dev_rating=5,
        best_for=["Fast development", "Agents", "Cost-effective"],
        notes="Excellent balance of speed, quality, and cost"
    ),

    # Gemini 2.0 Series
    "gemini-2.0-flash": ModelCapability(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider="google",
        context_window=1000000,
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_audio=True,
        supports_json_mode=True,
        latency_class="low",
        tier=PricingTier.FREE,  # Free tier available!
        category=ModelCategory.MULTIMODAL,
        specializations=["fast", "multimodal", "agents"],
        dev_rating=4,
        best_for=["Quick tasks", "Multimodal", "Free tier usage"],
        notes="Free tier available, good for development"
    ),

    "gemini-2.0-flash-lite": ModelCapability(
        id="gemini-2.0-flash-lite",
        name="Gemini 2.0 Flash Lite",
        provider="google",
        context_window=1000000,
        max_output_tokens=8192,
        supports_tools=True,
        supports_vision=True,
        supports_json_mode=True,
        latency_class="low",
        tier=PricingTier.FREE,
        category=ModelCategory.MULTIMODAL,
        specializations=["ultra-fast", "cost-effective"],
        dev_rating=3,
        best_for=["Simple tasks", "High volume"],
        notes="Fastest Gemini model"
    ),

    # Gemini 1.5 Series (Stable)
    "gemini-1.5-pro": ModelCapability(
        id="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        provider="google",
        context_window=2000000,  # 2M tokens!
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_audio=True,
        supports_json_mode=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        input_cost_per_million=1.25,
        output_cost_per_million=5.0,
        category=ModelCategory.MULTIMODAL,
        specializations=["ultra-long-context", "analysis"],
        dev_rating=5,
        best_for=["Very large codebases", "Long documents"],
        notes="Largest context window available - 2M tokens"
    ),

    "gemini-1.5-flash": ModelCapability(
        id="gemini-1.5-flash",
        name="Gemini 1.5 Flash",
        provider="google",
        context_window=1000000,
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        supports_audio=True,
        supports_json_mode=True,
        latency_class="low",
        tier=PricingTier.PAID,
        input_cost_per_million=0.075,
        output_cost_per_million=0.30,
        category=ModelCategory.MULTIMODAL,
        specializations=["fast", "long-context"],
        dev_rating=4,
        best_for=["Quick tasks with long context"],
        notes="Fast and cost-effective with 1M context"
    ),
}


# =============================================================================
# OPENROUTER MODELS - Gateway to 400+ Models
# =============================================================================

OPENROUTER_MODELS: Dict[str, ModelCapability] = {
    # Popular Models via OpenRouter
    "anthropic/claude-sonnet-4": ModelCapability(
        id="anthropic/claude-sonnet-4",
        name="Claude Sonnet 4 (via OpenRouter)",
        provider="openrouter",
        context_window=200000,
        max_output_tokens=16384,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        category=ModelCategory.MULTIMODAL,
        dev_rating=5,
        best_for=["Access via unified API"],
        notes="Claude via OpenRouter gateway"
    ),

    "openai/gpt-4o": ModelCapability(
        id="openai/gpt-4o",
        name="GPT-4o (via OpenRouter)",
        provider="openrouter",
        context_window=128000,
        max_output_tokens=16384,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        category=ModelCategory.MULTIMODAL,
        dev_rating=5,
        best_for=["Unified API access"],
        notes="GPT-4o via OpenRouter gateway"
    ),

    "google/gemini-2.5-flash": ModelCapability(
        id="google/gemini-2.5-flash",
        name="Gemini 2.5 Flash (via OpenRouter)",
        provider="openrouter",
        context_window=1000000,
        max_output_tokens=65536,
        supports_tools=True,
        supports_vision=True,
        latency_class="low",
        tier=PricingTier.PAID,
        category=ModelCategory.MULTIMODAL,
        dev_rating=5,
        best_for=["Fast + long context"],
        notes="Gemini via OpenRouter gateway"
    ),

    "meta-llama/llama-4-maverick": ModelCapability(
        id="meta-llama/llama-4-maverick",
        name="Llama 4 Maverick (via OpenRouter)",
        provider="openrouter",
        context_window=131072,
        max_output_tokens=8192,
        supports_tools=True,
        supports_parallel_tools=True,
        supports_vision=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        category=ModelCategory.MULTIMODAL,
        dev_rating=5,
        best_for=["Open-source via gateway"],
        notes="Llama 4 via OpenRouter"
    ),

    "mistralai/devstral-2": ModelCapability(
        id="mistralai/devstral-2",
        name="Devstral 2",
        provider="openrouter",
        context_window=262144,  # 256K
        max_output_tokens=32768,
        supports_tools=True,
        supports_parallel_tools=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        category=ModelCategory.CODING,
        specializations=["agentic-coding", "codebase-exploration"],
        dev_rating=5,
        best_for=["Code agents", "Multi-file changes"],
        notes="Specialized for agentic coding tasks"
    ),

    "qwen/qwen3-coder-480b": ModelCapability(
        id="qwen/qwen3-coder-480b",
        name="Qwen 3 Coder 480B",
        provider="openrouter",
        context_window=131072,
        max_output_tokens=16384,
        supports_tools=True,
        supports_parallel_tools=True,
        latency_class="high",
        tier=PricingTier.PAID,
        category=ModelCategory.CODING,
        specializations=["coding", "tool-use", "repository-reasoning"],
        dev_rating=5,
        best_for=["Complex coding", "Large repositories"],
        notes="Massive MoE model optimized for coding"
    ),

    "moonshotai/mimo-v2-flash": ModelCapability(
        id="moonshotai/mimo-v2-flash",
        name="MiMo V2 Flash",
        provider="openrouter",
        context_window=262144,  # 256K
        max_output_tokens=16384,
        supports_tools=True,
        supports_parallel_tools=True,
        latency_class="medium",
        tier=PricingTier.PAID,
        category=ModelCategory.REASONING,
        specializations=["reasoning", "coding", "agents"],
        dev_rating=4,
        best_for=["Reasoning tasks", "Agents"],
        notes="MoE model with hybrid thinking"
    ),

    # Free models on OpenRouter
    "meta-llama/llama-3.3-70b-instruct:free": ModelCapability(
        id="meta-llama/llama-3.3-70b-instruct:free",
        name="Llama 3.3 70B (Free)",
        provider="openrouter",
        context_window=131072,
        max_output_tokens=8192,
        supports_tools=True,
        latency_class="medium",
        tier=PricingTier.FREE,
        category=ModelCategory.LLM,
        dev_rating=4,
        best_for=["Free development", "Testing"],
        notes="Free tier with rate limits"
    ),

    "google/gemini-2.0-flash-exp:free": ModelCapability(
        id="google/gemini-2.0-flash-exp:free",
        name="Gemini 2.0 Flash Exp (Free)",
        provider="openrouter",
        context_window=1000000,
        max_output_tokens=8192,
        supports_tools=True,
        supports_vision=True,
        latency_class="low",
        tier=PricingTier.FREE,
        category=ModelCategory.MULTIMODAL,
        dev_rating=4,
        best_for=["Free development with vision"],
        notes="Free tier experimental model"
    ),
}


# =============================================================================
# UNIFIED ACCESS FUNCTIONS
# =============================================================================

def get_all_models() -> Dict[str, ModelCapability]:
    """Get all models from all providers."""
    all_models = {}
    all_models.update(GROQ_MODELS)
    all_models.update(ANTHROPIC_MODELS)
    all_models.update(OPENAI_MODELS)
    all_models.update(GOOGLE_MODELS)
    all_models.update(OPENROUTER_MODELS)
    return all_models


def get_models_by_provider(provider: str) -> Dict[str, ModelCapability]:
    """Get all models for a specific provider."""
    provider_map = {
        "groq": GROQ_MODELS,
        "anthropic": ANTHROPIC_MODELS,
        "openai": OPENAI_MODELS,
        "google": GOOGLE_MODELS,
        "openrouter": OPENROUTER_MODELS,
    }
    return provider_map.get(provider.lower(), {})


def get_model_capability(model_id: str) -> Optional[ModelCapability]:
    """Get capability info for a specific model."""
    all_models = get_all_models()

    # Direct match
    if model_id in all_models:
        return all_models[model_id]

    # Try case-insensitive match
    model_id_lower = model_id.lower()
    for key, value in all_models.items():
        if key.lower() == model_id_lower:
            return value

    # Try partial match
    for key, value in all_models.items():
        if model_id_lower in key.lower() or key.lower() in model_id_lower:
            return value

    return None


def get_free_models() -> Dict[str, ModelCapability]:
    """Get all free tier models."""
    return {k: v for k, v in get_all_models().items() if v.tier == PricingTier.FREE}


def get_models_with_tools() -> Dict[str, ModelCapability]:
    """Get all models that support tool/function calling."""
    return {k: v for k, v in get_all_models().items() if v.supports_tools}


def get_models_by_rating(min_rating: int = 4) -> Dict[str, ModelCapability]:
    """Get models with at least the specified dev rating."""
    return {k: v for k, v in get_all_models().items() if v.dev_rating >= min_rating}


def get_recommended_for_development() -> List[ModelCapability]:
    """Get top recommended models for development tasks."""
    all_models = get_all_models()

    # Filter and sort by dev_rating, then by context_window
    recommended = [
        m for m in all_models.values()
        if m.supports_tools and m.dev_rating >= 4 and m.category in [
            ModelCategory.LLM, ModelCategory.MULTIMODAL,
            ModelCategory.CODING, ModelCategory.REASONING
        ]
    ]

    return sorted(
        recommended,
        key=lambda x: (x.dev_rating, x.context_window),
        reverse=True
    )


def format_model_for_menu(model: ModelCapability) -> str:
    """Format model info for display in selection menu."""
    stars = "⭐" * model.dev_rating
    tier_icon = "🆓" if model.tier == PricingTier.FREE else "💰"
    vision_icon = "👁️" if model.supports_vision else ""
    tools_icon = "🔧" if model.supports_tools else "❌"

    context_str = f"{model.context_window // 1000}K"
    if model.context_window >= 1000000:
        context_str = f"{model.context_window // 1000000}M"

    return (
        f"{tier_icon} {model.name} {stars}\n"
        f"   {tools_icon} Tools  {vision_icon}  Context: {context_str}\n"
        f"   {', '.join(model.best_for[:2]) if model.best_for else 'General use'}"
    )


def get_model_summary(model_id: str) -> str:
    """Get a brief summary of model capabilities."""
    model = get_model_capability(model_id)
    if not model:
        return f"Unknown model: {model_id}"

    features = []
    if model.supports_tools:
        features.append("Tools")
    if model.supports_parallel_tools:
        features.append("Parallel Tools")
    if model.supports_vision:
        features.append("Vision")
    if model.supports_audio:
        features.append("Audio")

    context_str = f"{model.context_window:,}" if model.context_window > 0 else "N/A"

    return (
        f"Model: {model.name} ({model.provider})\n"
        f"Context: {context_str} tokens\n"
        f"Features: {', '.join(features) if features else 'Text only'}\n"
        f"Tier: {model.tier.value}\n"
        f"Rating: {'⭐' * model.dev_rating} ({model.dev_rating}/5)\n"
        f"Best for: {', '.join(model.best_for) if model.best_for else 'General use'}"
    )
