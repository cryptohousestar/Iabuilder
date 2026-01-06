"""Model registry for caching and managing models from multiple providers.

This module provides a unified registry for discovering and caching models
from all configured LLM providers.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from .provider_config import get_multi_provider_config_manager


@dataclass
class ModelInfo:
    """Information about a model."""

    id: str
    provider: str
    name: str
    context_length: int = 0
    supports_function_calling: bool = False
    description: str = ""
    category: str = "llm"
    metadata: Dict[str, Any] = None
    cached_at: str = ""
    is_free: bool = False  # For OpenRouter: indicates if model is free

    def __post_init__(self):
        """Initialize defaults."""
        if self.metadata is None:
            self.metadata = {}
        if not self.cached_at:
            self.cached_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInfo':
        """Create from dictionary."""
        return cls(**data)

    def matches_query(self, query: str) -> bool:
        """Check if model matches search query.

        Args:
            query: Search query (case-insensitive)

        Returns:
            True if matches, False otherwise
        """
        query = query.lower()
        return (
            query in self.id.lower()
            or query in self.name.lower()
            or query in self.description.lower()
            or query in self.provider.lower()
            or query in self.category.lower()
        )


class ModelCache:
    """Cache for model information."""

    def __init__(self, cache_file: Path, expiry_hours: int = 1):
        """Initialize model cache.

        Args:
            cache_file: Path to cache file
            expiry_hours: Hours before cache expires (default: 1)
        """
        self.cache_file = cache_file
        self.expiry_hours = expiry_hours
        self.models: Dict[str, ModelInfo] = {}
        self.last_refresh: Optional[datetime] = None

        # Load existing cache
        self._load_cache()

    def _load_cache(self):
        """Load cache from file."""
        if not self.cache_file.exists():
            return

        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)

            # Parse models
            self.models = {
                model_id: ModelInfo.from_dict(model_data)
                for model_id, model_data in data.get('models', {}).items()
            }

            # Parse last refresh
            if 'last_refresh' in data:
                self.last_refresh = datetime.fromisoformat(data['last_refresh'])

        except Exception as e:
            print(f"Warning: Failed to load model cache: {e}")
            self.models = {}
            self.last_refresh = None

    def _save_cache(self):
        """Save cache to file."""
        data = {
            'version': '1.0',
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'models': {
                model_id: model.to_dict()
                for model_id, model in self.models.items()
            }
        }

        # Ensure directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)

    def is_expired(self) -> bool:
        """Check if cache is expired.

        Returns:
            True if expired or never refreshed, False otherwise
        """
        if self.last_refresh is None:
            return True

        expiry_time = self.last_refresh + timedelta(hours=self.expiry_hours)
        return datetime.now() > expiry_time

    def update_models(self, provider: str, models: List[Dict[str, Any]]):
        """Update models for a specific provider.

        Args:
            provider: Provider name
            models: List of model dictionaries
        """
        # Remove old models from this provider
        self.models = {
            model_id: model
            for model_id, model in self.models.items()
            if model.provider != provider
        }

        # Add new models
        for model_data in models:
            model_info = ModelInfo(
                id=model_data['id'],
                provider=provider,
                name=model_data.get('name', model_data['id']),
                context_length=model_data.get('context_length', 0),
                supports_function_calling=model_data.get('supports_function_calling', False),
                description=model_data.get('description', ''),
                category=model_data.get('category', 'llm'),
                metadata=model_data.get('metadata', {}),
                is_free=model_data.get('is_free', False),
            )
            self.models[model_info.id] = model_info

        self.last_refresh = datetime.now()
        self._save_cache()

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get model by ID.

        Args:
            model_id: Model identifier

        Returns:
            ModelInfo if found, None otherwise
        """
        return self.models.get(model_id)

    def get_models_by_provider(self, provider: str) -> List[ModelInfo]:
        """Get all models from a specific provider.

        Args:
            provider: Provider name

        Returns:
            List of ModelInfo objects
        """
        return [
            model
            for model in self.models.values()
            if model.provider == provider
        ]

    def get_all_models(self) -> List[ModelInfo]:
        """Get all cached models.

        Returns:
            List of ModelInfo objects
        """
        return list(self.models.values())

    def search_models(self, query: str) -> List[ModelInfo]:
        """Search models by query.

        Args:
            query: Search query

        Returns:
            List of matching ModelInfo objects
        """
        return [
            model
            for model in self.models.values()
            if model.matches_query(query)
        ]

    def clear(self):
        """Clear all cached models."""
        self.models = {}
        self.last_refresh = None
        self._save_cache()


class ModelRegistry:
    """Registry for managing models from multiple providers.

    Features:
    - Caches models from all configured providers
    - Auto-refresh on startup and expiry
    - Search and filter capabilities
    - Fallback to static model lists
    """

    def __init__(
        self,
        cache_file: Optional[Path] = None,
        expiry_hours: int = 1,
        auto_refresh: bool = True
    ):
        """Initialize model registry.

        Args:
            cache_file: Path to cache file (defaults to ~/.iabuilder/model_cache.json)
            expiry_hours: Hours before cache expires (default: 1)
            auto_refresh: Whether to auto-refresh on startup if expired
        """
        if cache_file is None:
            config_dir = Path.home() / ".iabuilder"
            cache_file = config_dir / "model_cache.json"

        self.cache = ModelCache(cache_file, expiry_hours)
        self.provider_manager = get_multi_provider_config_manager()

        # Auto-refresh if expired
        if auto_refresh and self.cache.is_expired():
            # Schedule async refresh (will run when event loop is available)
            self._schedule_refresh()

    def _schedule_refresh(self):
        """Schedule an async refresh of models."""
        try:
            # Try to get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run refresh in background
            if loop.is_running():
                asyncio.create_task(self.refresh_models())
            else:
                loop.run_until_complete(self.refresh_models())
        except Exception as e:
            print(f"Warning: Failed to auto-refresh models: {e}")

    async def refresh_models(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Refresh models from provider(s).

        Args:
            provider_name: Specific provider to refresh, or None for all

        Returns:
            Dictionary with refresh results:
            {
                'success': bool,
                'providers_refreshed': List[str],
                'providers_failed': List[str],
                'total_models': int,
                'errors': Dict[str, str]
            }
        """
        results = {
            'success': True,
            'providers_refreshed': [],
            'providers_failed': [],
            'total_models': 0,
            'errors': {}
        }

        # Get providers to refresh
        if provider_name:
            providers = {provider_name: self.provider_manager.get_provider_config(provider_name)}
            if providers[provider_name] is None:
                results['success'] = False
                results['errors'][provider_name] = "Provider not found"
                return results
        else:
            providers = self.provider_manager.list_providers(enabled_only=True)

        # Import provider classes dynamically
        from ..providers import (
            GroqProvider,
            OpenAIProvider,
            AnthropicProvider,
            GoogleProvider,
            OpenRouterProvider,
            AIMLProvider
        )

        provider_classes = {
            'groq': GroqProvider,
            'openai': OpenAIProvider,
            'anthropic': AnthropicProvider,
            'google': GoogleProvider,
            'openrouter': OpenRouterProvider,
            'aiml': AIMLProvider,
        }

        # Refresh each provider
        for name, config in providers.items():
            if not config.enabled:
                continue

            try:
                # Get API key (with env override)
                api_key = self.provider_manager.get_provider_api_key(name)
                if not api_key:
                    results['providers_failed'].append(name)
                    results['errors'][name] = "No API key configured"
                    continue

                # Get provider class
                provider_class = provider_classes.get(name)
                if not provider_class:
                    # Try to use fallback models
                    results['providers_failed'].append(name)
                    results['errors'][name] = f"Provider class not found for '{name}'"
                    continue

                # Initialize provider
                provider = provider_class(
                    api_key=api_key,
                    model=config.default_model or "",
                    base_url=config.base_url
                )

                # List models
                try:
                    models = await provider.list_available_models()
                except Exception as api_error:
                    # Fallback to static models
                    print(f"Warning: Failed to fetch models for {name}, using fallback: {api_error}")
                    models = provider.get_fallback_models()

                # Update cache
                self.cache.update_models(name, models)

                results['providers_refreshed'].append(name)
                results['total_models'] += len(models)

            except Exception as e:
                results['success'] = False
                results['providers_failed'].append(name)
                results['errors'][name] = str(e)

        return results

    def get_available_models(
        self,
        provider: Optional[str] = None,
        category: Optional[str] = None,
        supports_function_calling: Optional[bool] = None
    ) -> List[ModelInfo]:
        """Get available models with optional filters.

        Args:
            provider: Filter by provider name
            category: Filter by category (e.g., 'llm', 'vision')
            supports_function_calling: Filter by function calling support

        Returns:
            List of ModelInfo objects
        """
        models = self.cache.get_all_models()

        # Apply filters
        if provider:
            models = [m for m in models if m.provider == provider]

        if category:
            models = [m for m in models if m.category == category]

        if supports_function_calling is not None:
            models = [m for m in models if m.supports_function_calling == supports_function_calling]

        return models

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model.

        Args:
            model_id: Model identifier

        Returns:
            ModelInfo if found, None otherwise
        """
        return self.cache.get_model(model_id)

    def search_models(
        self,
        query: str,
        provider: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[ModelInfo]:
        """Search for models matching query.

        Args:
            query: Search query (matches ID, name, description, etc.)
            provider: Optional provider filter
            category: Optional category filter

        Returns:
            List of matching ModelInfo objects
        """
        models = self.cache.search_models(query)

        # Apply filters
        if provider:
            models = [m for m in models if m.provider == provider]

        if category:
            models = [m for m in models if m.category == category]

        return models

    def add_manual_model(
        self,
        model_id: str,
        provider: str,
        name: Optional[str] = None,
        context_length: int = 0,
        supports_function_calling: bool = False,
        description: str = "",
        category: str = "llm",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ModelInfo:
        """Manually add a model to the registry.

        Useful for providers that don't support model listing or custom models.

        Args:
            model_id: Model identifier
            provider: Provider name
            name: Optional display name
            context_length: Context window size
            supports_function_calling: Whether model supports function calling
            description: Model description
            category: Model category
            metadata: Additional metadata

        Returns:
            Created ModelInfo
        """
        model_info = ModelInfo(
            id=model_id,
            provider=provider,
            name=name or model_id,
            context_length=context_length,
            supports_function_calling=supports_function_calling,
            description=description,
            category=category,
            metadata=metadata or {}
        )

        self.cache.models[model_id] = model_info
        self.cache._save_cache()

        return model_info

    def remove_model(self, model_id: str) -> bool:
        """Remove a model from the cache.

        Args:
            model_id: Model identifier

        Returns:
            True if removed, False if not found
        """
        if model_id in self.cache.models:
            del self.cache.models[model_id]
            self.cache._save_cache()
            return True
        return False

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the cache.

        Returns:
            Dictionary with cache metadata
        """
        return {
            'total_models': len(self.cache.models),
            'providers': list(set(m.provider for m in self.cache.models.values())),
            'last_refresh': self.cache.last_refresh.isoformat() if self.cache.last_refresh else None,
            'is_expired': self.cache.is_expired(),
            'expiry_hours': self.cache.expiry_hours,
            'cache_file': str(self.cache.cache_file),
        }

    def clear_cache(self):
        """Clear the entire model cache."""
        self.cache.clear()


# Global instance
_model_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get or create global model registry instance.

    Returns:
        ModelRegistry instance
    """
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry(auto_refresh=True)
    return _model_registry
