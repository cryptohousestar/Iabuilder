"""Multi-provider configuration manager for IABuilder.

This module manages API keys and configuration for multiple LLM providers
including Groq, OpenAI, Anthropic, Google, and OpenRouter.
"""

import os
import base64
import hashlib
import platform
import getpass
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import yaml
from pydantic import BaseModel, Field, field_validator

# Try to import cryptography for real encryption
try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


class ProviderConfig(BaseModel):
    """Configuration for a single provider."""

    name: str = Field(..., description="Provider name (e.g., 'groq', 'openai')")
    api_key: str = Field(..., description="API key for the provider")
    base_url: Optional[str] = Field(None, description="Custom base URL (optional)")
    default_model: Optional[str] = Field(None, description="Default model for this provider")
    enabled: bool = Field(True, description="Whether this provider is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    added_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="When provider was added")
    last_validated: Optional[str] = Field(None, description="Last validation timestamp")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate provider name."""
        if not v or not v.strip():
            raise ValueError("Provider name cannot be empty")
        return v.strip().lower()

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key."""
        if not v or not v.strip():
            raise ValueError("API key cannot be empty")
        return v.strip()


class ProviderRegistry(BaseModel):
    """Registry of all configured providers."""

    version: str = Field(default="1.0", description="Config format version")
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict, description="Provider configurations")
    active_provider: Optional[str] = Field(None, description="Currently active provider")

    class Config:
        extra = "allow"


class MultiProviderConfigManager:
    """Manages configuration for multiple LLM providers.

    Features:
    - Secure storage of API keys in ~/.iabuilder/providers.yaml
    - Add/remove/list providers
    - Validate provider configurations
    - Optional encryption for API keys
    - Backward compatibility with single-provider config
    """

    # Known provider prefixes for validation
    KNOWN_PREFIXES = {
        "groq": ["gsk_"],
        "openai": ["sk-"],
        "anthropic": ["sk-ant-"],
        "google": ["AIza"],
        "openrouter": ["sk-or-"],
        "aiml": [""],  # AIML uses UUID format without prefix
        "ollama": ["ollama", ""],  # Ollama doesn't need API key
    }

    # Default base URLs for known providers
    DEFAULT_BASE_URLS = {
        "groq": "https://api.groq.com/openai/v1",
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "openrouter": "https://openrouter.ai/api/v1",
        "aiml": "https://api.aimlapi.com/v1",
        "ollama": "http://localhost:11434/v1",
    }

    def __init__(self, config_dir: Optional[Path] = None, use_encryption: bool = True):
        """Initialize the multi-provider config manager.

        Args:
            config_dir: Custom config directory. Defaults to ~/.iabuilder
            use_encryption: Whether to encrypt API keys (default: True for security)
        """
        self.config_dir = config_dir or Path.home() / ".iabuilder"
        self.config_file = self.config_dir / "providers.yaml"
        self.key_file = self.config_dir / ".encryption_key"
        self.use_encryption = use_encryption and ENCRYPTION_AVAILABLE
        self._fernet = None

        # Ensure directory exists with secure permissions
        self.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Initialize encryption if available
        if self.use_encryption:
            self._init_encryption()

        # Initialize or load registry
        self.registry = self._load_or_create_registry()

    def _init_encryption(self):
        """Initialize Fernet encryption with a machine-specific key."""
        try:
            if self.key_file.exists():
                # Load existing key
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate a new key based on machine identity
                # This ties the encryption to this specific machine/user
                machine_id = self._get_machine_id()
                key = self._derive_key(machine_id)

                # Save the key with secure permissions
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                os.chmod(self.key_file, 0o600)

            self._fernet = Fernet(key)
        except Exception as e:
            print(f"Warning: Could not initialize encryption: {e}")
            self.use_encryption = False

    def _get_machine_id(self) -> str:
        """Get a unique machine identifier for key derivation."""
        components = [
            platform.node(),  # Hostname
            getpass.getuser(),  # Username
            str(Path.home()),  # Home directory
            platform.machine(),  # Machine type
        ]
        return "|".join(components)

    def _derive_key(self, seed: str) -> bytes:
        """Derive a Fernet-compatible key from a seed string."""
        # Use SHA256 to get consistent 32 bytes, then base64 encode for Fernet
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        return base64.urlsafe_b64encode(hash_bytes)

    def _load_or_create_registry(self) -> ProviderRegistry:
        """Load existing registry or create a new one.

        Returns:
            ProviderRegistry instance
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = yaml.safe_load(f) or {}

                # Decrypt API keys if encryption is enabled
                if self.use_encryption and 'providers' in data:
                    for provider_name, provider_data in data['providers'].items():
                        if 'api_key' in provider_data:
                            provider_data['api_key'] = self._decrypt(provider_data['api_key'])

                return ProviderRegistry(**data)
            except Exception as e:
                print(f"Warning: Failed to load providers config: {e}")
                print("Creating new config...")

        # Create new registry
        return ProviderRegistry()

    def _save_registry(self):
        """Save registry to file with secure permissions."""
        data = self.registry.model_dump()

        # Always encrypt API keys (encryption is now enabled by default)
        if 'providers' in data:
            for provider_name, provider_data in data['providers'].items():
                if 'api_key' in provider_data:
                    api_key = provider_data['api_key']
                    # Only encrypt if not already encrypted
                    if not api_key.startswith("ENC:") and not api_key.startswith("B64:"):
                        provider_data['api_key'] = self._encrypt(api_key)

        with open(self.config_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        # Set secure permissions
        try:
            os.chmod(self.config_file, 0o600)
        except Exception:
            pass  # Best effort

    def _encrypt(self, value: str) -> str:
        """Encrypt a value using Fernet symmetric encryption.

        Args:
            value: String to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if self._fernet:
            try:
                encrypted = self._fernet.encrypt(value.encode())
                return f"ENC:{encrypted.decode()}"
            except Exception as e:
                print(f"Warning: Encryption failed: {e}")

        # Fallback to base64 obfuscation if encryption unavailable
        return f"B64:{base64.b64encode(value.encode()).decode()}"

    def _decrypt(self, value: str) -> str:
        """Decrypt a value using Fernet symmetric encryption.

        Args:
            value: String to decrypt

        Returns:
            Decrypted string
        """
        try:
            if value.startswith("ENC:") and self._fernet:
                # Fernet encrypted value
                encrypted_data = value[4:]
                return self._fernet.decrypt(encrypted_data.encode()).decode()
            elif value.startswith("B64:"):
                # Base64 obfuscated value
                return base64.b64decode(value[4:].encode()).decode()
            else:
                # Plain text (legacy or migration) - return as-is
                return value
        except Exception as e:
            print(f"Warning: Decryption failed: {e}")
            # Return as-is if decryption fails
            return value

    def add_provider(
        self,
        name: str,
        api_key: str,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        set_active: bool = False
    ) -> ProviderConfig:
        """Add or update a provider configuration.

        Args:
            name: Provider name (e.g., 'groq', 'openai')
            api_key: API key for the provider
            base_url: Optional custom base URL
            default_model: Optional default model
            metadata: Optional additional metadata
            set_active: Whether to set this as active provider

        Returns:
            Created/updated ProviderConfig

        Raises:
            ValueError: If provider name or API key is invalid
        """
        # Normalize name
        name = name.strip().lower()

        # Use default base URL if not provided
        if base_url is None and name in self.DEFAULT_BASE_URLS:
            base_url = self.DEFAULT_BASE_URLS[name]

        # Create provider config
        provider = ProviderConfig(
            name=name,
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            metadata=metadata or {},
        )

        # Add to registry
        self.registry.providers[name] = provider

        # Set as active if requested or if it's the first provider
        if set_active or not self.registry.active_provider:
            self.registry.active_provider = name

        # Save to file
        self._save_registry()

        return provider

    def remove_provider(self, name: str) -> bool:
        """Remove a provider from configuration.

        Args:
            name: Provider name to remove

        Returns:
            True if removed, False if not found
        """
        name = name.strip().lower()

        if name not in self.registry.providers:
            return False

        del self.registry.providers[name]

        # If this was the active provider, switch to another
        if self.registry.active_provider == name:
            if self.registry.providers:
                self.registry.active_provider = next(iter(self.registry.providers.keys()))
            else:
                self.registry.active_provider = None

        self._save_registry()
        return True

    def get_provider_config(self, name: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider.

        Args:
            name: Provider name

        Returns:
            ProviderConfig if found, None otherwise
        """
        name = name.strip().lower()
        return self.registry.providers.get(name)

    def list_providers(self, enabled_only: bool = False) -> Dict[str, ProviderConfig]:
        """List all configured providers.

        Args:
            enabled_only: If True, only return enabled providers

        Returns:
            Dictionary mapping provider names to ProviderConfig objects
        """
        if enabled_only:
            return {
                name: config
                for name, config in self.registry.providers.items()
                if config.enabled
            }
        return self.registry.providers.copy()

    def validate_provider(self, name: str) -> tuple[bool, str]:
        """Validate a provider's configuration.

        Args:
            name: Provider name to validate

        Returns:
            Tuple of (is_valid, message)
        """
        name = name.strip().lower()
        provider = self.get_provider_config(name)

        if not provider:
            return False, f"Provider '{name}' not found"

        # Check API key format for known providers
        if name in self.KNOWN_PREFIXES:
            prefixes = self.KNOWN_PREFIXES[name]
            if not any(provider.api_key.startswith(prefix) for prefix in prefixes):
                expected = "' or '".join(prefixes)
                return False, f"API key should start with '{expected}'"

        # Basic validation passed
        provider.last_validated = datetime.now().isoformat()
        self._save_registry()

        return True, "Provider configuration is valid"

    def get_active_provider(self) -> Optional[ProviderConfig]:
        """Get the currently active provider.

        Returns:
            Active ProviderConfig or None
        """
        if self.registry.active_provider:
            return self.get_provider_config(self.registry.active_provider)
        return None

    def set_active_provider(self, name: str) -> bool:
        """Set the active provider.

        Args:
            name: Provider name to set as active

        Returns:
            True if set successfully, False if provider not found
        """
        name = name.strip().lower()
        if name not in self.registry.providers:
            return False

        self.registry.active_provider = name
        self._save_registry()
        return True

    def enable_provider(self, name: str, enabled: bool = True) -> bool:
        """Enable or disable a provider.

        Args:
            name: Provider name
            enabled: Whether to enable (True) or disable (False)

        Returns:
            True if updated, False if provider not found
        """
        name = name.strip().lower()
        provider = self.get_provider_config(name)

        if not provider:
            return False

        provider.enabled = enabled
        self._save_registry()
        return True

    def migrate_from_legacy_config(self, api_key: str, provider_name: str = "groq") -> bool:
        """Migrate from legacy single-provider config.

        Args:
            api_key: Legacy API key
            provider_name: Provider name for the legacy key

        Returns:
            True if migration successful
        """
        if provider_name in self.registry.providers:
            print(f"Provider '{provider_name}' already exists, skipping migration")
            return False

        self.add_provider(
            name=provider_name,
            api_key=api_key,
            set_active=True,
            metadata={"migrated": True, "migrated_at": datetime.now().isoformat()}
        )

        print(f"Migrated legacy config to provider '{provider_name}'")
        return True

    def get_env_override(self, provider_name: str) -> Optional[str]:
        """Check for environment variable override for provider API key.

        Args:
            provider_name: Provider name

        Returns:
            API key from environment or None
        """
        # Check provider-specific env var
        env_var = f"{provider_name.upper()}_API_KEY"
        api_key = os.getenv(env_var)

        if api_key:
            return api_key

        # Check generic GROQ_API_KEY for backward compatibility
        if provider_name == "groq":
            return os.getenv("GROQ_API_KEY")

        return None

    def get_provider_api_key(self, provider_name: str) -> Optional[str]:
        """Get API key for a provider, checking environment first.

        Args:
            provider_name: Provider name

        Returns:
            API key or None
        """
        # Check environment first
        env_key = self.get_env_override(provider_name)
        if env_key:
            return env_key

        # Get from config
        provider = self.get_provider_config(provider_name)
        if provider:
            return provider.api_key

        return None


# Global instance
_config_manager: Optional[MultiProviderConfigManager] = None


def get_multi_provider_config_manager() -> MultiProviderConfigManager:
    """Get or create global multi-provider config manager instance.

    Returns:
        MultiProviderConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = MultiProviderConfigManager()
    return _config_manager
