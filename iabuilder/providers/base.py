"""Abstract base class for LLM providers.

This module defines the interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Iterator, List, Optional, Union


class ModelProvider(ABC):
    """Abstract base class for all LLM providers.

    This class defines the common interface that all LLM providers
    (Groq, OpenAI, Anthropic, Google, etc.) must implement.
    """

    def __init__(self, api_key: str, model: str, **kwargs):
        """Initialize the provider.

        Args:
            api_key: API key for the provider
            model: Default model to use
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.model = model
        self.config = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name.

        Returns:
            Provider name (e.g., "groq", "openai", "anthropic")
        """
        pass

    @abstractmethod
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List models available from this provider.

        Returns:
            List of model dictionaries with metadata:
            - id: Model identifier
            - name: Human-readable name
            - context_length: Maximum context window
            - supports_function_calling: Whether model supports function calling
            - description: Model description

        Raises:
            Exception: If API call fails
        """
        pass

    @abstractmethod
    def get_fallback_models(self) -> List[Dict[str, Any]]:
        """Get fallback model list (static).

        This method returns a hardcoded list of models as a fallback
        when the API is unavailable.

        Returns:
            List of model dictionaries with same format as list_available_models
        """
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stream: bool = False,
        callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> Any:
        """Send chat completion request.

        Args:
            messages: List of message dictionaries with role and content
            model: Model to use (defaults to self.model)
            tools: Optional list of tool/function definitions
            tool_choice: Tool choice mode ("auto", "none", or specific tool)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 to 2.0)
            stream: Whether to stream the response
            callback: Optional callback for streaming chunks
            **kwargs: Additional provider-specific parameters

        Returns:
            Chat completion response object (provider-specific format)

        Raises:
            Exception: If API call fails
        """
        pass

    @abstractmethod
    def validate_api_key(self) -> bool:
        """Validate that the API key is properly formatted.

        Returns:
            True if API key appears valid, False otherwise
        """
        pass

    @abstractmethod
    def categorize_models(self) -> Dict[str, List[str]]:
        """Categorize available models by type.

        Returns:
            Dictionary mapping category names to lists of model IDs.
            Common categories: "llm", "vision", "embedding", "tts", "whisper", etc.
        """
        pass

    @abstractmethod
    def supports_function_calling(self, model: Optional[str] = None) -> bool:
        """Check if a model supports function calling.

        Args:
            model: Model to check (defaults to self.model)

        Returns:
            True if model supports function calling, False otherwise
        """
        pass

    def switch_model(self, model: str):
        """Switch to a different model.

        Args:
            model: Model identifier
        """
        self.model = model

    def get_current_model(self) -> str:
        """Get the current model.

        Returns:
            Current model identifier
        """
        return self.model


class ProviderError(Exception):
    """Base exception for provider-related errors."""
    pass


class AuthenticationError(ProviderError):
    """Raised when API authentication fails."""
    pass


class ModelNotFoundError(ProviderError):
    """Raised when requested model is not available."""
    pass


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""
    pass


class APIError(ProviderError):
    """Raised for general API errors."""
    pass
