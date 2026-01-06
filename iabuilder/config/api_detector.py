"""API format detection for multi-provider support.

This module detects the API format and capabilities of different LLM providers
based on their API keys, base URLs, and response formats.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class APIFormat(Enum):
    """Supported API formats."""

    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    UNKNOWN = "unknown"


@dataclass
class APICapabilities:
    """Capabilities of an API provider."""

    format: APIFormat
    supports_streaming: bool = True
    supports_function_calling: bool = True
    supports_vision: bool = False
    supports_embeddings: bool = False
    max_context_length: int = 8192
    requires_system_message: bool = False
    message_format: str = "openai"  # "openai", "anthropic", "google"


class APIDetector:
    """Detects API format and capabilities from API keys and configurations."""

    # API key prefixes for different providers
    API_KEY_PATTERNS = {
        APIFormat.GROQ: r"^gsk_",
        APIFormat.OPENAI: r"^sk-[a-zA-Z0-9]{20,}",
        APIFormat.ANTHROPIC: r"^sk-ant-",
        APIFormat.GOOGLE: r"^AIza[a-zA-Z0-9_-]{33,}",
        APIFormat.AZURE: r"^[a-f0-9]{32}$",
    }

    # Base URL patterns for different providers
    BASE_URL_PATTERNS = {
        APIFormat.GROQ: r"groq\.com|api\.groq",
        APIFormat.OPENAI: r"api\.openai\.com",
        APIFormat.ANTHROPIC: r"api\.anthropic\.com",
        APIFormat.GOOGLE: r"generativelanguage\.googleapis\.com",
        APIFormat.AZURE: r"openai\.azure\.com",
    }

    @classmethod
    def detect_from_api_key(cls, api_key: str) -> APIFormat:
        """Detect provider from API key format.

        Args:
            api_key: API key to analyze

        Returns:
            Detected API format
        """
        if not api_key or not api_key.strip():
            return APIFormat.UNKNOWN

        for format_type, pattern in cls.API_KEY_PATTERNS.items():
            if re.match(pattern, api_key.strip()):
                return format_type

        return APIFormat.UNKNOWN

    @classmethod
    def detect_from_base_url(cls, base_url: str) -> APIFormat:
        """Detect provider from base URL.

        Args:
            base_url: Base URL to analyze

        Returns:
            Detected API format
        """
        if not base_url:
            return APIFormat.UNKNOWN

        base_url = base_url.lower()
        for format_type, pattern in cls.BASE_URL_PATTERNS.items():
            if re.search(pattern, base_url):
                return format_type

        return APIFormat.UNKNOWN

    @classmethod
    def detect_format(
        cls,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> APIFormat:
        """Detect API format from multiple sources.

        Args:
            api_key: API key to analyze
            base_url: Base URL to analyze
            provider_name: Explicit provider name

        Returns:
            Detected API format
        """
        # Check explicit provider name first
        if provider_name:
            provider_lower = provider_name.lower()
            for format_type in APIFormat:
                if format_type.value == provider_lower:
                    return format_type

        # Check base URL
        if base_url:
            url_format = cls.detect_from_base_url(base_url)
            if url_format != APIFormat.UNKNOWN:
                return url_format

        # Check API key
        if api_key:
            key_format = cls.detect_from_api_key(api_key)
            if key_format != APIFormat.UNKNOWN:
                return key_format

        return APIFormat.UNKNOWN

    @classmethod
    def get_capabilities(cls, api_format: APIFormat) -> APICapabilities:
        """Get capabilities for a specific API format.

        Args:
            api_format: API format to get capabilities for

        Returns:
            APICapabilities object with provider-specific settings
        """
        if api_format == APIFormat.GROQ:
            return APICapabilities(
                format=api_format,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=False,
                supports_embeddings=False,
                max_context_length=128000,
                requires_system_message=False,
                message_format="openai",
            )

        elif api_format == APIFormat.OPENAI:
            return APICapabilities(
                format=api_format,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                supports_embeddings=True,
                max_context_length=128000,
                requires_system_message=False,
                message_format="openai",
            )

        elif api_format == APIFormat.ANTHROPIC:
            return APICapabilities(
                format=api_format,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                supports_embeddings=False,
                max_context_length=200000,
                requires_system_message=True,
                message_format="anthropic",
            )

        elif api_format == APIFormat.GOOGLE:
            return APICapabilities(
                format=api_format,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                supports_embeddings=False,
                max_context_length=32000,
                requires_system_message=False,
                message_format="google",
            )

        elif api_format == APIFormat.AZURE:
            return APICapabilities(
                format=api_format,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                supports_embeddings=True,
                max_context_length=128000,
                requires_system_message=False,
                message_format="openai",
            )

        else:  # UNKNOWN
            return APICapabilities(
                format=api_format,
                supports_streaming=True,
                supports_function_calling=False,
                supports_vision=False,
                supports_embeddings=False,
                max_context_length=8192,
                requires_system_message=False,
                message_format="openai",
            )

    @classmethod
    def is_openai_compatible(cls, api_format: APIFormat) -> bool:
        """Check if API format is OpenAI-compatible.

        Args:
            api_format: API format to check

        Returns:
            True if OpenAI-compatible (can use same client library)
        """
        return api_format in [APIFormat.GROQ, APIFormat.OPENAI, APIFormat.AZURE]

    @classmethod
    def validate_configuration(
        cls,
        api_key: str,
        base_url: Optional[str] = None,
        expected_format: Optional[APIFormat] = None,
    ) -> Dict[str, Any]:
        """Validate API configuration and detect issues.

        Args:
            api_key: API key to validate
            base_url: Optional base URL
            expected_format: Expected API format (for validation)

        Returns:
            Dictionary with validation results:
            - valid: bool
            - detected_format: APIFormat
            - issues: List[str]
            - warnings: List[str]
        """
        issues = []
        warnings = []

        # Detect format
        detected_format = cls.detect_format(api_key=api_key, base_url=base_url)

        # Check if detected format matches expected
        if expected_format and detected_format != expected_format:
            if detected_format == APIFormat.UNKNOWN:
                warnings.append(
                    f"Could not detect API format. Expected {expected_format.value}"
                )
            else:
                issues.append(
                    f"API key appears to be for {detected_format.value}, "
                    f"but {expected_format.value} was expected"
                )

        # Validate API key format
        if not api_key or not api_key.strip():
            issues.append("API key is empty")
        elif detected_format == APIFormat.UNKNOWN:
            warnings.append("API key format not recognized")

        # Check base URL compatibility
        if base_url:
            url_format = cls.detect_from_base_url(base_url)
            if url_format != APIFormat.UNKNOWN and url_format != detected_format:
                warnings.append(
                    f"Base URL appears to be for {url_format.value}, "
                    f"but API key is for {detected_format.value}"
                )

        return {
            "valid": len(issues) == 0,
            "detected_format": detected_format,
            "issues": issues,
            "warnings": warnings,
        }

    @classmethod
    def get_provider_info(cls, api_format: APIFormat) -> Dict[str, Any]:
        """Get detailed information about a provider.

        Args:
            api_format: API format to get info for

        Returns:
            Dictionary with provider information
        """
        info = {
            APIFormat.GROQ: {
                "name": "Groq",
                "website": "https://groq.com",
                "docs": "https://console.groq.com/docs",
                "signup": "https://console.groq.com",
                "key_prefix": "gsk_",
            },
            APIFormat.OPENAI: {
                "name": "OpenAI",
                "website": "https://openai.com",
                "docs": "https://platform.openai.com/docs",
                "signup": "https://platform.openai.com/signup",
                "key_prefix": "sk-",
            },
            APIFormat.ANTHROPIC: {
                "name": "Anthropic",
                "website": "https://anthropic.com",
                "docs": "https://docs.anthropic.com",
                "signup": "https://console.anthropic.com",
                "key_prefix": "sk-ant-",
            },
            APIFormat.GOOGLE: {
                "name": "Google AI",
                "website": "https://ai.google.dev",
                "docs": "https://ai.google.dev/docs",
                "signup": "https://makersuite.google.com",
                "key_prefix": "AIza",
            },
            APIFormat.AZURE: {
                "name": "Azure OpenAI",
                "website": "https://azure.microsoft.com/en-us/products/ai-services/openai-service",
                "docs": "https://learn.microsoft.com/en-us/azure/ai-services/openai/",
                "signup": "https://portal.azure.com",
                "key_prefix": "[32-char hex]",
            },
        }

        return info.get(
            api_format,
            {
                "name": "Unknown Provider",
                "website": "",
                "docs": "",
                "signup": "",
                "key_prefix": "",
            },
        )
