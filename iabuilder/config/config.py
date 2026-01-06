"""Configuration management for Groq CLI."""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Configuration model for Groq CLI."""

    api_key: str = Field(..., description="Groq API key")
    default_model: str = Field(
        default="llama-3.1-8b-instant", description="Default model to use"
    )
    max_tokens: int = Field(default=8000, description="Maximum tokens for responses")
    temperature: float = Field(
        default=0.5, ge=0.0, le=2.0, description="Model temperature (0.5 recommended for coding)"
    )
    auto_save: bool = Field(default=True, description="Auto-save conversations")
    safe_mode: bool = Field(default=False, description="Confirm destructive operations")
    streaming: bool = Field(default=True, description="Enable streaming responses (see text as it's generated)")
    autorun: bool = Field(default=True, description="Auto-run tools without confirmation (12 iteration limit)")
    toolbox: bool = Field(default=True, description="Enable tools/function calling (ON=tools, OFF=chat only)")

    class Config:
        extra = "allow"  # Allow additional fields


class ConfigManager:
    """Manages configuration loading, saving, and validation."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Custom config directory. Defaults to ~/.iabuilder
        """
        self.config_dir = config_dir or Path.home() / ".iabuilder"
        self.config_file = self.config_dir / "config.json"
        self.history_dir = self.config_dir / "history"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

        # Set secure permissions on config directory
        try:
            os.chmod(self.config_dir, 0o700)
        except Exception:
            pass  # Best effort

    def load(self) -> Config:
        """Load configuration from file or environment.

        Priority:
        1. Environment variables (GROQ_API_KEY)
        2. Config file (~/.iabuilder/config.json)
        3. First-run setup wizard

        Returns:
            Config object
        """
        # Try to load from file
        config_data = {}
        if self.config_file.exists():
            with open(self.config_file) as f:
                config_data = json.load(f)

        # Override with environment variables
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            config_data["api_key"] = api_key

        # If no API key found, run first-time setup
        if "api_key" not in config_data:
            config_data = self._first_run_setup()

        return Config(**config_data)

    def save(self, config: Config):
        """Save configuration to file.

        Args:
            config: Config object to save
        """
        # Don't save API key if it's from environment
        config_dict = config.model_dump()
        if os.getenv("GROQ_API_KEY"):
            # Save a placeholder instead
            config_dict["api_key"] = "<from_environment>"

        with open(self.config_file, "w") as f:
            json.dump(config_dict, f, indent=2)

        # Set secure permissions on config file
        try:
            os.chmod(self.config_file, 0o600)
        except Exception:
            pass  # Best effort

    def _first_run_setup(self) -> dict:
        """Interactive first-run setup wizard.

        Returns:
            Dictionary with initial configuration
        """
        from rich.console import Console
        from rich.panel import Panel

        console = Console()

        console.print(
            Panel.fit(
                "[bold cyan]Welcome to Groq CLI![/bold cyan]\n\n"
                "Let's set up your configuration.",
                title="First Run Setup",
            )
        )

        # Get API key
        api_key = input("\nEnter your Groq API key: ").strip()
        while not api_key:
            console.print("[red]API key cannot be empty![/red]")
            api_key = input("Enter your Groq API key: ").strip()

        # Default configuration
        config_data = {
            "api_key": api_key,
            "default_model": "llama-3.3-70b-versatile",
            "max_tokens": 8000,
            "temperature": 0.5,  # Lower for more precise code
            "auto_save": True,
            "safe_mode": False,
        }

        # Save to file
        with open(self.config_file, "w") as f:
            json.dump(config_data, f, indent=2)

        # Set secure permissions
        try:
            os.chmod(self.config_file, 0o600)
        except Exception:
            pass

        console.print(f"\n[green]✓[/green] Configuration saved to {self.config_file}")
        console.print(
            "[dim]You can edit this file or set GROQ_API_KEY environment variable.[/dim]\n"
        )

        return config_data

    def update(self, **kwargs):
        """Update configuration with new values.

        Args:
            **kwargs: Configuration keys to update
        """
        config = self.load()

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        self.save(config)


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create global config manager instance.

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_config() -> Config:
    """Convenience function to load configuration.

    Returns:
        Config object
    """
    return get_config_manager().load()
