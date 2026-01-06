"""Bootstrap module for IABuilder initialization."""

import os
import signal
import sys
from pathlib import Path
from typing import Optional

from ..cli import CLI
from ..client import GroqClient
from ..config import get_config_manager, load_config
from ..conversation import Conversation
from ..intent_classifier import IntentClassifier
from ..project_explorer import ProjectExplorer
from ..renderer import Renderer
from ..splash_screen import SplashScreen
from ..config.provider_config import get_multi_provider_config_manager
from ..config.model_registry import get_model_registry
from ..errors import get_error_handler


class AppBootstrap:
    """Handles application initialization and setup."""

    def __init__(self, working_directory: Optional[str] = None):
        """Initialize bootstrap.

        Args:
            working_directory: Directory to work in (defaults to current directory)
        """
        self.renderer = Renderer()
        self.error_handler = get_error_handler()
        self.working_directory = self._setup_working_directory(working_directory)

    def _setup_working_directory(self, working_directory: Optional[str]) -> Path:
        """Setup and change to working directory.

        Args:
            working_directory: Directory path or None for current

        Returns:
            Resolved Path object
        """
        if working_directory:
            work_dir = Path(working_directory).resolve()
        else:
            work_dir = Path.cwd()

        os.chdir(work_dir)
        self.renderer.render_info(f"🔄 Working directory: {work_dir}")
        return work_dir

    def show_splash_screen(self) -> bool:
        """Show splash screen and return if this is first run.

        Returns:
            True if first run, False otherwise
        """
        splash = SplashScreen()
        config_path = Path.home() / ".iabuilder" / "config.yaml"
        is_first_run = not config_path.exists()

        if is_first_run:
            print(splash.get_first_run_splash())
        else:
            print(splash.get_minimal_splash())

        return is_first_run

    def initialize_config(self):
        """Initialize configuration managers.

        Returns:
            Tuple of (config_manager, config, provider_config, model_registry)
        """
        try:
            config_manager = get_config_manager()
            config = load_config()
            provider_config = get_multi_provider_config_manager()
            model_registry = get_model_registry()

            return config_manager, config, provider_config, model_registry

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={"phase": "config_initialization"}
            )
            raise

    def explore_project(self) -> tuple:
        """Explore current project and return context.

        Returns:
            Tuple of (project_explorer, project_context)
        """
        try:
            project_explorer = ProjectExplorer(self.working_directory)
            project_context = project_explorer.explore_project()

            # Show project summary
            project_summary = project_explorer.get_project_summary()
            self.renderer.render_info("📋 Project Context:")
            for line in project_summary.split('\n'):
                if line.strip():
                    self.renderer.render_info(line)

            return project_explorer, project_context

        except Exception as e:
            self.error_handler.log_warning(
                f"Could not explore project: {e}",
                context={"working_directory": str(self.working_directory)}
            )
            return None, {}

    def initialize_components(self, config, project_context=None):
        """Initialize core components.

        Args:
            config: Application configuration
            project_context: Project context from explore_project()

        Returns:
            Tuple of (conversation, cli, client, intent_classifier)
        """
        try:
            conversation = Conversation(
                auto_save=config.auto_save,
                project_context=project_context
            )
            cli = CLI(conversation=conversation)

            # Get API key from active provider (multi-provider system)
            # Falls back to legacy config.api_key for backward compatibility
            provider_config = get_multi_provider_config_manager()
            active_provider = provider_config.get_active_provider()

            # Default models for each provider
            default_models = {
                "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
                "openai": "gpt-4o-mini",
                "groq": "llama-3.3-70b-versatile",
                "anthropic": "claude-3-5-sonnet-20241022",
            }

            if active_provider:
                api_key = active_provider.api_key
                provider_name = active_provider.name
                # Use provider's default model, or fall back to our defaults
                model = (
                    active_provider.default_model or
                    default_models.get(provider_name) or
                    config.default_model
                )
                self.renderer.render_info(
                    f"🔑 Using provider: {provider_name.upper()}"
                )
            else:
                # Fallback to legacy config
                api_key = config.api_key
                model = config.default_model
                provider_name = "groq"  # Default to groq
                if api_key:
                    self.renderer.render_info(
                        "🔑 Using legacy API key from config"
                    )
                else:
                    self.renderer.render_warning(
                        "⚠️  No API key configured! Use /configure-api to set up a provider."
                    )

            # Create appropriate client based on provider
            client = self._create_client(provider_name, api_key or "", model)
            intent_classifier = IntentClassifier()

            # Update CLI with correct model from active provider
            cli.current_model = model

            return conversation, cli, client, intent_classifier

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={"phase": "component_initialization"},
                raise_error=True
            )

    def _create_client(self, provider_name: str, api_key: str, model: str):
        """Create the appropriate client for the provider.

        Args:
            provider_name: Name of the provider (groq, openrouter, etc.)
            api_key: API key for the provider
            model: Model to use

        Returns:
            Client instance (GroqClient or OpenAICompatibleClient)
        """
        provider_name = provider_name.lower()

        if provider_name == "openrouter":
            from ..client_openai import OpenAICompatibleClient
            return OpenAICompatibleClient(
                api_key=api_key,
                model=model,
                base_url="https://openrouter.ai/api/v1"
            )
        elif provider_name == "openai":
            from ..client_openai import OpenAICompatibleClient
            return OpenAICompatibleClient(
                api_key=api_key,
                model=model,
                base_url=None  # Use default OpenAI URL
            )
        elif provider_name == "groq":
            return GroqClient(api_key=api_key, model=model)
        elif provider_name == "aiml":
            from ..client_openai import OpenAICompatibleClient
            return OpenAICompatibleClient(
                api_key=api_key,
                model=model,
                base_url="https://api.aimlapi.com/v1"
            )
        else:
            # For other providers, try OpenAI-compatible mode
            provider_config = get_multi_provider_config_manager()
            config = provider_config.get_provider_config(provider_name)
            if config and config.base_url:
                from ..client_openai import OpenAICompatibleClient
                return OpenAICompatibleClient(
                    api_key=api_key,
                    model=model,
                    base_url=config.base_url
                )
            # Default to Groq client
            return GroqClient(api_key=api_key, model=model)

    def setup_rate_limiting(self, model_name: str, tier: str = "free", provider: str = "groq"):
        """Setup rate limiting for the model.

        Args:
            model_name: Name of the model
            tier: Tier level (free or paid)
            provider: Provider name (groq, openrouter, etc.)
        """
        try:
            from ..rate_limiter import set_rate_limiter
            set_rate_limiter(model_name=model_name, tier=tier, provider=provider)
            self.renderer.render_info(
                f"⏱️  Rate limiting: {provider.upper()}/{model_name}"
            )
        except Exception as e:
            self.error_handler.log_warning(
                f"Could not setup rate limiting: {e}"
            )

    def setup_signal_handlers(self, cleanup_callback):
        """Setup signal handlers for graceful shutdown.

        Args:
            cleanup_callback: Function to call on shutdown
        """
        def signal_handler(signum, frame):
            self.renderer.render_info("\n🛑 Shutting down gracefully...")
            cleanup_callback()
            sys.exit(0)

        # Multi-platform signal handling
        signal.signal(signal.SIGINT, signal_handler)

        # SIGTERM only available on Unix-like systems
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)

    def show_provider_status(self, provider_config):
        """Show status of configured providers.

        Args:
            provider_config: Provider configuration manager
        """
        try:
            providers = provider_config.list_providers()
            if providers:
                active = provider_config.get_active_provider()
                self.renderer.render_info(
                    f"🔌 Providers: {len(providers)} configured"
                    + (f" | Active: {active}" if active else "")
                )
            else:
                self.renderer.render_info(
                    "💡 No providers configured. Use /configure-api to get started"
                )
        except Exception as e:
            self.error_handler.log_debug(
                f"Could not show provider status: {e}"
            )
