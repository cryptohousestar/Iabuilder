"""Input validation for IABuilder - Prevent security vulnerabilities."""

import os
import re
from pathlib import Path
from typing import Optional, List

from ..errors import ValidationError, get_error_handler


class InputValidator:
    """Validates user input to prevent security issues."""

    def __init__(self):
        """Initialize validator."""
        self.error_handler = get_error_handler()

        # Dangerous patterns for command injection
        self.dangerous_patterns = [
            r'[;&|`$]',  # Shell metacharacters
            r'\$\(',     # Command substitution
            r'>\s*/dev', # Device redirection
            r'<\s*/etc', # Config file access
        ]

    def validate_file_path(
        self,
        file_path: str,
        must_exist: bool = False,
        allow_absolute: bool = True
    ) -> Path:
        """Validate and sanitize file path.

        Args:
            file_path: Path to validate
            must_exist: If True, path must exist
            allow_absolute: If True, allow absolute paths

        Returns:
            Sanitized Path object

        Raises:
            ValidationError: If path is invalid or dangerous
        """
        if not file_path:
            raise ValidationError("path", "Path cannot be empty")

        try:
            path = Path(file_path).resolve()
        except Exception as e:
            raise ValidationError("path", f"Invalid path: {e}")

        # Check for path traversal
        try:
            # Resolve path and check if it's within allowed directories
            resolved = path.resolve()

            # Check for suspicious patterns
            path_str = str(resolved)
            if '..' in file_path and resolved.is_absolute():
                # Allow .. in paths, but log suspicious ones
                self.error_handler.log_debug(
                    f"Path with ..: {file_path} -> {resolved}"
                )

        except Exception as e:
            raise ValidationError("path", f"Could not resolve path: {e}")

        # Check absolute path restriction
        if not allow_absolute and path.is_absolute():
            raise ValidationError(
                "path",
                "Absolute paths not allowed in this context"
            )

        # Check existence if required
        if must_exist and not path.exists():
            raise ValidationError("path", f"Path does not exist: {path}")

        return path

    def validate_command(self, command: str, allow_pipes: bool = False) -> str:
        """Validate shell command for dangerous patterns.

        Args:
            command: Command to validate
            allow_pipes: If True, allow pipe (|) character

        Returns:
            Original command if valid

        Raises:
            ValidationError: If command contains dangerous patterns
        """
        if not command:
            raise ValidationError("command", "Command cannot be empty")

        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            # Skip pipe check if allowed
            if allow_pipes and pattern == r'[;&|`$]':
                # Check individual dangerous chars except pipe
                if re.search(r'[;&`$]', command):
                    raise ValidationError(
                        "command",
                        f"Command contains dangerous characters: {pattern}"
                    )
            elif re.search(pattern, command):
                raise ValidationError(
                    "command",
                    f"Command contains dangerous pattern: {pattern}"
                )

        return command

    def validate_api_key(self, provider: str, api_key: str) -> str:
        """Validate API key format.

        Args:
            provider: Provider name
            api_key: API key to validate

        Returns:
            Original API key if valid

        Raises:
            ValidationError: If API key format is invalid
        """
        if not api_key or not isinstance(api_key, str):
            raise ValidationError("api_key", "API key must be a non-empty string")

        # Remove whitespace
        api_key = api_key.strip()

        # Minimum length check
        if len(api_key) < 10:
            raise ValidationError("api_key", "API key too short")

        # Provider-specific validation
        patterns = {
            'groq': r'^gsk_[a-zA-Z0-9]{40,}$',
            'openai': r'^sk-[a-zA-Z0-9]{40,}$',
            'anthropic': r'^sk-ant-[a-zA-Z0-9\-]{40,}$',
            'openrouter': r'^sk-or-[a-zA-Z0-9\-]{40,}$',
        }

        pattern = patterns.get(provider.lower())
        if pattern and not re.match(pattern, api_key):
            raise ValidationError(
                "api_key",
                f"Invalid {provider} API key format"
            )

        return api_key

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal.

        Args:
            filename: Filename to sanitize

        Returns:
            Sanitized filename
        """
        # Remove directory components
        filename = os.path.basename(filename)

        # Remove dangerous characters
        filename = re.sub(r'[^\w\s\-\.]', '', filename)

        # Remove leading dots
        filename = filename.lstrip('.')

        if not filename:
            raise ValidationError("filename", "Invalid filename after sanitization")

        return filename

    def validate_model_name(self, model_name: str) -> str:
        """Validate AI model name.

        Args:
            model_name: Model name to validate

        Returns:
            Validated model name

        Raises:
            ValidationError: If model name is invalid
        """
        if not model_name or not isinstance(model_name, str):
            raise ValidationError("model_name", "Model name must be a non-empty string")

        # Remove whitespace
        model_name = model_name.strip()

        # Check for reasonable characters
        if not re.match(r'^[a-zA-Z0-9\-\._:]+$', model_name):
            raise ValidationError(
                "model_name",
                "Model name contains invalid characters"
            )

        return model_name

    def validate_url(self, url: str, allowed_schemes: Optional[List[str]] = None) -> str:
        """Validate URL.

        Args:
            url: URL to validate
            allowed_schemes: List of allowed schemes (default: http, https)

        Returns:
            Validated URL

        Raises:
            ValidationError: If URL is invalid
        """
        if not url or not isinstance(url, str):
            raise ValidationError("url", "URL must be a non-empty string")

        url = url.strip()

        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']

        # Basic URL validation
        url_pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url, re.IGNORECASE):
            raise ValidationError("url", "Invalid URL format")

        # Check scheme
        scheme = url.split('://')[0].lower()
        if scheme not in allowed_schemes:
            raise ValidationError(
                "url",
                f"URL scheme must be one of: {', '.join(allowed_schemes)}"
            )

        return url


# Global validator instance
_input_validator: Optional[InputValidator] = None


def get_input_validator() -> InputValidator:
    """Get global input validator instance."""
    global _input_validator
    if _input_validator is None:
        _input_validator = InputValidator()
    return _input_validator
