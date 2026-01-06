"""Configuration management and API detection for multi-provider support."""

from .api_detector import APICapabilities, APIDetector, APIFormat
from .config import Config, ConfigManager, get_config_manager, load_config
from .provider_config import (
    MultiProviderConfigManager,
    ProviderConfig,
    ProviderRegistry,
    get_multi_provider_config_manager,
)
from .model_registry import (
    ModelRegistry,
    ModelInfo,
    ModelCache,
    get_model_registry,
)

__all__ = [
    # Legacy config
    "Config",
    "ConfigManager",
    "get_config_manager",
    "load_config",
    # API detection
    "APIDetector",
    "APIFormat",
    "APICapabilities",
    # Multi-provider config
    "MultiProviderConfigManager",
    "ProviderConfig",
    "ProviderRegistry",
    "get_multi_provider_config_manager",
    # Model registry
    "ModelRegistry",
    "ModelInfo",
    "ModelCache",
    "get_model_registry",
]
