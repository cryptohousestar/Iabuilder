"""Credential management for IABuilder - Secure API key storage."""

import os
import platform
from pathlib import Path
from typing import Optional, Dict
import yaml
import base64

from ..errors import get_error_handler, ConfigError


class CredentialManager:
    """Manages API credentials securely using system keyring."""

    def __init__(self):
        """Initialize credential manager."""
        self.error_handler = get_error_handler()
        self._keyring_available = self._check_keyring()

    def _check_keyring(self) -> bool:
        """Check if keyring is available."""
        try:
            import keyring
            # Test if keyring backend is accessible
            keyring.get_keyring()
            return True
        except Exception as e:
            self.error_handler.log_warning(
                f"Keyring not available: {e}. Using fallback storage."
            )
            return False

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider.

        Priority:
        1. Environment variable
        2. System keyring
        3. Config file (fallback)

        Args:
            provider: Provider name (groq, openai, anthropic, etc.)

        Returns:
            API key or None
        """
        provider = provider.lower()

        # 1. Check environment variable first
        env_var = f"{provider.upper()}_API_KEY"
        api_key = os.environ.get(env_var)
        if api_key:
            self.error_handler.log_debug(
                f"Using API key from environment: {env_var}"
            )
            return api_key

        # 2. Try keyring (if available)
        if self._keyring_available:
            api_key = self._get_from_keyring(provider)
            if api_key:
                return api_key

        # 3. Fallback to config file
        return self._get_from_config(provider)

    def save_api_key(self, provider: str, api_key: str) -> bool:
        """Save API key securely.

        Args:
            provider: Provider name
            api_key: API key to save

        Returns:
            True if saved successfully
        """
        provider = provider.lower()

        # Validate API key format
        if not self._validate_api_key(provider, api_key):
            raise ConfigError(
                f"Invalid API key format for {provider}",
                config_file="credentials"
            )

        # Try to save to keyring first
        if self._keyring_available:
            if self._save_to_keyring(provider, api_key):
                self.error_handler.log_info(
                    f"API key saved to system keyring: {provider}"
                )
                return True

        # Fallback to config file
        return self._save_to_config(provider, api_key)

    def delete_api_key(self, provider: str) -> bool:
        """Delete API key for a provider.

        Args:
            provider: Provider name

        Returns:
            True if deleted successfully
        """
        provider = provider.lower()
        deleted = False

        # Delete from keyring
        if self._keyring_available:
            deleted = self._delete_from_keyring(provider) or deleted

        # Delete from config
        deleted = self._delete_from_config(provider) or deleted

        return deleted

    def list_providers(self) -> list:
        """List all providers with stored credentials.

        Returns:
            List of provider names
        """
        providers = set()

        # Check environment variables
        for key in os.environ:
            if key.endswith("_API_KEY"):
                provider = key.replace("_API_KEY", "").lower()
                providers.add(provider)

        # Check config file
        config_providers = self._list_from_config()
        providers.update(config_providers)

        return sorted(list(providers))

    def migrate_from_base64(self) -> int:
        """Migrate credentials from base64 encoding to keyring.

        Returns:
            Number of credentials migrated
        """
        config_file = self._get_config_file()
        if not config_file.exists():
            return 0

        migrated = 0

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f) or {}

            for provider, data in config.items():
                if isinstance(data, dict) and 'api_key_encoded' in data:
                    # Decode from base64
                    try:
                        encoded = data['api_key_encoded']
                        api_key = base64.b64decode(encoded).decode('utf-8')

                        # Save to keyring
                        if self.save_api_key(provider, api_key):
                            # Remove from config file
                            del config[provider]['api_key_encoded']
                            if not config[provider]:
                                del config[provider]
                            migrated += 1

                    except Exception as e:
                        self.error_handler.log_warning(
                            f"Could not migrate {provider}: {e}"
                        )

            # Save cleaned config
            with open(config_file, 'w') as f:
                yaml.dump(config, f)

            if migrated > 0:
                self.error_handler.log_info(
                    f"Migrated {migrated} credentials to secure storage"
                )

        except Exception as e:
            self.error_handler.log_error(
                f"Migration failed: {e}"
            )

        return migrated

    # Private methods

    def _get_from_keyring(self, provider: str) -> Optional[str]:
        """Get API key from system keyring."""
        try:
            import keyring
            api_key = keyring.get_password("iabuilder", provider)
            if api_key:
                self.error_handler.log_debug(
                    f"Retrieved API key from keyring: {provider}"
                )
            return api_key
        except Exception as e:
            self.error_handler.log_debug(
                f"Could not get from keyring: {e}"
            )
            return None

    def _save_to_keyring(self, provider: str, api_key: str) -> bool:
        """Save API key to system keyring."""
        try:
            import keyring
            keyring.set_password("iabuilder", provider, api_key)
            return True
        except Exception as e:
            self.error_handler.log_warning(
                f"Could not save to keyring: {e}"
            )
            return False

    def _delete_from_keyring(self, provider: str) -> bool:
        """Delete API key from keyring."""
        try:
            import keyring
            keyring.delete_password("iabuilder", provider)
            return True
        except Exception:
            return False

    def _get_from_config(self, provider: str) -> Optional[str]:
        """Get API key from config file (fallback)."""
        config_file = self._get_config_file()
        if not config_file.exists():
            return None

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f) or {}

            provider_config = config.get(provider, {})
            if isinstance(provider_config, dict):
                return provider_config.get('api_key')

        except Exception as e:
            self.error_handler.log_warning(
                f"Could not read config file: {e}"
            )

        return None

    def _save_to_config(self, provider: str, api_key: str) -> bool:
        """Save API key to config file (fallback)."""
        config_file = self._get_config_file()
        config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Load existing config
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}

            # Update provider config
            if provider not in config:
                config[provider] = {}
            config[provider]['api_key'] = api_key

            # Save with restricted permissions (Linux)
            with open(config_file, 'w') as f:
                yaml.dump(config, f)

            # Set file permissions to 600 (owner read/write only)
            if platform.system() != "Windows":
                config_file.chmod(0o600)

            self.error_handler.log_info(
                f"API key saved to config file: {provider}"
            )
            return True

        except Exception as e:
            self.error_handler.log_error(
                f"Could not save to config: {e}"
            )
            return False

    def _delete_from_config(self, provider: str) -> bool:
        """Delete API key from config file."""
        config_file = self._get_config_file()
        if not config_file.exists():
            return False

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f) or {}

            if provider in config:
                del config[provider]

                with open(config_file, 'w') as f:
                    yaml.dump(config, f)

                return True

        except Exception as e:
            self.error_handler.log_warning(
                f"Could not delete from config: {e}"
            )

        return False

    def _list_from_config(self) -> list:
        """List providers from config file."""
        config_file = self._get_config_file()
        if not config_file.exists():
            return []

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
            return list(config.keys())
        except:
            return []

    @staticmethod
    def _get_config_file() -> Path:
        """Get config file path (platform-specific)."""
        if platform.system() == "Windows":
            # Windows: %APPDATA%\iabuilder\credentials.yaml
            base = Path(os.environ.get("APPDATA", Path.home()))
        else:
            # Linux/macOS: ~/.iabuilder/credentials.yaml
            base = Path.home()

        return base / ".iabuilder" / "credentials.yaml"

    def _validate_api_key(self, provider: str, api_key: str) -> bool:
        """Validate API key format for provider.

        Args:
            provider: Provider name
            api_key: API key to validate

        Returns:
            True if valid format
        """
        if not api_key or not isinstance(api_key, str):
            return False

        # Provider-specific validation
        patterns = {
            'groq': lambda k: k.startswith('gsk_') and len(k) > 20,
            'openai': lambda k: k.startswith('sk-') and len(k) > 20,
            'anthropic': lambda k: k.startswith('sk-ant-') and len(k) > 20,
            'google': lambda k: len(k) > 20,  # Generic validation
            'openrouter': lambda k: k.startswith('sk-or-') and len(k) > 20,
        }

        validator = patterns.get(provider)
        if validator:
            return validator(api_key)

        # Generic validation for unknown providers
        return len(api_key) > 10


# Global instance
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """Get global credential manager instance."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager
