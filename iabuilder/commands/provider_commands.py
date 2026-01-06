"""Provider management commands for IABuilder.

Commands for configuring and managing multiple LLM providers.
"""

import asyncio
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ..config.provider_config import get_multi_provider_config_manager
from ..config.model_registry import get_model_registry


console = Console()


def configure_api_command(provider: Optional[str] = None) -> bool:
    """Configure API key for a preset provider.

    Usage:
        /configure-api groq
        /configure-api openai
        /configure-api anthropic
        /configure-api google
        /configure-api openrouter

    Args:
        provider: Provider name (groq, openai, anthropic, google, openrouter)

    Returns:
        True if successful, False otherwise
    """
    config_manager = get_multi_provider_config_manager()

    # Known providers
    known_providers = {
        "groq": {
            "name": "Groq",
            "url": "https://console.groq.com/keys",
            "key_prefix": "gsk_",
        },
        "openai": {
            "name": "OpenAI",
            "url": "https://platform.openai.com/api-keys",
            "key_prefix": "sk-",
        },
        "anthropic": {
            "name": "Anthropic",
            "url": "https://console.anthropic.com/settings/keys",
            "key_prefix": "sk-ant-",
        },
        "google": {
            "name": "Google AI",
            "url": "https://makersuite.google.com/app/apikey",
            "key_prefix": "AIza",
        },
        "openrouter": {
            "name": "OpenRouter",
            "url": "https://openrouter.ai/keys",
            "key_prefix": "sk-or-",
        },
        "aiml": {
            "name": "AIML API",
            "url": "https://docs.aimlapi.com/quickstart/setting-up",
            "key_prefix": "",  # UUID format, no specific prefix
        },
    }

    # If no provider specified, show menu
    if not provider:
        console.print("\n[bold cyan]Configure API Provider[/bold cyan]\n")
        console.print("Available providers:")
        for i, (key, info) in enumerate(known_providers.items(), 1):
            console.print(f"  {i}. {info['name']} ({key})")
        console.print()

        choice = Prompt.ask(
            "Select provider",
            choices=[str(i) for i in range(1, len(known_providers) + 1)],
            default="1"
        )
        provider = list(known_providers.keys())[int(choice) - 1]

    # Validate provider
    provider = provider.lower().strip()
    if provider not in known_providers:
        console.print(f"[red]Error: Unknown provider '{provider}'[/red]")
        console.print(f"Available providers: {', '.join(known_providers.keys())}")
        return False

    provider_info = known_providers[provider]

    # Show provider info
    console.print(
        Panel.fit(
            f"[bold]{provider_info['name']}[/bold]\n\n"
            f"Get your API key from: [link={provider_info['url']}]{provider_info['url']}[/link]\n"
            f"API keys start with: [cyan]{provider_info['key_prefix']}[/cyan]",
            title=f"Configure {provider_info['name']}",
            border_style="cyan",
        )
    )

    # Get API key (visible input for easier pasting)
    api_key = Prompt.ask(
        f"\nEnter your {provider_info['name']} API key"
    ).strip()

    if not api_key:
        console.print("[red]Error: API key cannot be empty[/red]")
        return False

    # Validate key format
    if not api_key.startswith(provider_info['key_prefix']):
        console.print(
            f"[yellow]Warning: API key doesn't start with expected prefix '{provider_info['key_prefix']}'[/yellow]"
        )
        if not Confirm.ask("Continue anyway?", default=False):
            return False

    # Get default model (optional)
    default_model = Prompt.ask(
        f"Default model for {provider_info['name']} (optional, press Enter to skip)",
        default=""
    ).strip()

    # Set as active provider
    set_active = Confirm.ask(
        f"Set {provider_info['name']} as active provider?",
        default=True
    )

    try:
        # Add provider
        config_manager.add_provider(
            name=provider,
            api_key=api_key,
            default_model=default_model or None,
            set_active=set_active
        )

        console.print(f"\n[green]Success! {provider_info['name']} configured.[/green]")

        if set_active:
            console.print(f"[dim]{provider_info['name']} is now the active provider.[/dim]")

        return True

    except Exception as e:
        console.print(f"[red]Error: Failed to configure provider: {e}[/red]")
        return False


def add_provider_command() -> bool:
    """Add a custom provider interactively.

    Usage:
        /add-provider

    Returns:
        True if successful, False otherwise
    """
    config_manager = get_multi_provider_config_manager()

    console.print("\n[bold cyan]Add Custom Provider[/bold cyan]\n")

    # Get provider details
    name = Prompt.ask("Provider name (e.g., 'custom', 'local')").strip().lower()
    if not name:
        console.print("[red]Error: Provider name cannot be empty[/red]")
        return False

    # Check if exists
    existing = config_manager.get_provider_config(name)
    if existing:
        console.print(f"[yellow]Warning: Provider '{name}' already exists[/yellow]")
        if not Confirm.ask("Overwrite?", default=False):
            return False

    api_key = Prompt.ask("API key").strip()
    if not api_key:
        console.print("[red]Error: API key cannot be empty[/red]")
        return False

    base_url = Prompt.ask(
        "Base URL (e.g., https://api.example.com/v1, press Enter to skip)",
        default=""
    ).strip()

    default_model = Prompt.ask(
        "Default model (press Enter to skip)",
        default=""
    ).strip()

    set_active = Confirm.ask("Set as active provider?", default=True)

    try:
        config_manager.add_provider(
            name=name,
            api_key=api_key,
            base_url=base_url or None,
            default_model=default_model or None,
            set_active=set_active
        )

        console.print(f"\n[green]Success! Provider '{name}' added.[/green]")
        return True

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


def remove_api_command(provider: Optional[str] = None) -> bool:
    """Remove a provider configuration.

    Usage:
        /remove-api groq
        /remove-api openai

    Args:
        provider: Provider name to remove

    Returns:
        True if successful, False otherwise
    """
    config_manager = get_multi_provider_config_manager()

    # If no provider specified, show list
    if not provider:
        providers = config_manager.list_providers()
        if not providers:
            console.print("[yellow]No providers configured[/yellow]")
            return False

        console.print("\n[bold cyan]Remove Provider[/bold cyan]\n")
        console.print("Configured providers:")
        provider_list = list(providers.keys())
        for i, name in enumerate(provider_list, 1):
            console.print(f"  {i}. {name}")
        console.print()

        choice = Prompt.ask(
            "Select provider to remove",
            choices=[str(i) for i in range(1, len(provider_list) + 1)]
        )
        provider = provider_list[int(choice) - 1]

    # Validate provider exists
    provider = provider.lower().strip()
    if not config_manager.get_provider_config(provider):
        console.print(f"[red]Error: Provider '{provider}' not found[/red]")
        return False

    # Confirm removal
    if not Confirm.ask(f"Remove provider '{provider}'?", default=False):
        console.print("[dim]Cancelled[/dim]")
        return False

    # Remove provider
    if config_manager.remove_provider(provider):
        console.print(f"[green]Provider '{provider}' removed[/green]")
        return True
    else:
        console.print(f"[red]Failed to remove provider '{provider}'[/red]")
        return False


def status_command() -> bool:
    """Show status of all configured providers.

    Usage:
        /status

    Returns:
        True if successful, False otherwise
    """
    config_manager = get_multi_provider_config_manager()

    providers = config_manager.list_providers()

    if not providers:
        console.print(
            Panel.fit(
                "[yellow]No providers configured[/yellow]\n\n"
                "Use [cyan]/configure-api[/cyan] to add a provider.",
                title="Provider Status",
                border_style="yellow",
            )
        )
        return True

    # Create table
    table = Table(title="Provider Status", show_header=True, header_style="bold cyan")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("API Key", style="dim")
    table.add_column("Default Model", style="green")
    table.add_column("Base URL", style="dim")
    table.add_column("Active", justify="center")

    active_provider = config_manager.registry.active_provider

    for name, config in providers.items():
        # Status
        is_valid, msg = config_manager.validate_provider(name)
        status = "[green]Valid[/green]" if is_valid else "[red]Invalid[/red]"
        if not config.enabled:
            status = "[dim]Disabled[/dim]"

        # API key (masked)
        api_key_masked = config.api_key[:8] + "..." if len(config.api_key) > 8 else "***"

        # Active marker
        is_active = "Yes" if name == active_provider else ""

        # Add row
        table.add_row(
            name,
            status,
            api_key_masked,
            config.default_model or "-",
            config.base_url or "-",
            is_active
        )

    console.print()
    console.print(table)
    console.print()

    # Show usage hint
    console.print(
        "[dim]Commands: /configure-api <provider> | /add-provider | /remove-api <provider>[/dim]"
    )
    console.print()

    return True


def provider_command(provider_name: Optional[str] = None) -> str:
    """Switch active API provider and optionally select a model.

    Shows a table of configured providers and allows switching between them.
    After selecting a provider, shows available models to choose from.

    Usage:
        /provider           - Show providers and switch interactively
        /provider openrouter - Switch directly to openrouter

    Args:
        provider_name: Optional provider name to switch to directly

    Returns:
        Status message
    """
    config_manager = get_multi_provider_config_manager()
    providers = config_manager.list_providers()

    if not providers:
        console.print(
            Panel.fit(
                "[yellow]No hay proveedores configurados[/yellow]\n\n"
                "Usa [cyan]/configure-api[/cyan] para agregar un proveedor.",
                title="📡 Proveedores",
                border_style="yellow",
            )
        )
        return "No hay proveedores configurados"

    # Show providers table
    console.print("\n[bold cyan]📡 APIs Configuradas:[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", justify="right", style="dim", width=5)
    table.add_column("Proveedor", style="cyan", width=17)
    table.add_column("Modelo por Defecto", style="green", width=32)
    table.add_column("Estado", justify="center", width=12)

    active_provider = config_manager.registry.active_provider
    provider_list = list(providers.keys())

    for i, name in enumerate(provider_list, 1):
        config = providers[name]

        # Status
        if name == active_provider:
            status = "[green]✅ Activo[/green]"
        elif config.enabled:
            status = "[dim]Disponible[/dim]"
        else:
            status = "[red]Deshabilitado[/red]"

        table.add_row(
            str(i),
            name.upper(),
            config.default_model or "[dim]No configurado[/dim]",
            status
        )

    console.print(table)
    console.print()

    # If provider specified, switch directly
    if provider_name:
        provider_name = provider_name.lower().strip()
        if provider_name not in provider_list:
            return f"❌ Proveedor '{provider_name}' no encontrado"
    else:
        # Ask user to select
        if len(provider_list) == 1:
            console.print("[dim]Solo hay un proveedor configurado.[/dim]")
            provider_name = provider_list[0]
        else:
            choice = Prompt.ask(
                "Selecciona proveedor",
                choices=[str(i) for i in range(1, len(provider_list) + 1)],
                default="1"
            )
            provider_name = provider_list[int(choice) - 1]

    # Check if already active
    if provider_name == active_provider:
        console.print(f"[dim]{provider_name.upper()} ya está activo[/dim]")
    else:
        # Set as active
        config_manager.set_active_provider(provider_name)
        console.print(f"\n[green]✅ Proveedor activo: {provider_name.upper()}[/green]")

    # Ask if user wants to see/select models
    show_models = Confirm.ask(
        f"\n¿Ver modelos disponibles de {provider_name.upper()}?",
        default=True
    )

    if show_models:
        selected_model = _show_provider_models(provider_name)
        if selected_model:
            return f"✅ Proveedor: {provider_name.upper()} | Modelo: {selected_model}"

    return f"✅ Proveedor activo: {provider_name.upper()}"


def _show_provider_models(provider_name: str) -> Optional[str]:
    """Show and allow selection of models from a provider.

    Args:
        provider_name: Provider to fetch models from

    Returns:
        Selected model ID or None
    """
    config_manager = get_multi_provider_config_manager()
    model_registry = get_model_registry()

    console.print(f"\n[cyan]🔄 Obteniendo modelos de {provider_name.upper()}...[/cyan]")

    try:
        # Try to fetch fresh models from API
        models = _fetch_models_sync(provider_name)

        if not models:
            console.print("[yellow]No se pudieron obtener modelos de la API[/yellow]")
            # Try cached models
            cached_models = model_registry.get_available_models(provider=provider_name)
            if cached_models:
                models = [{"id": m.id, "name": m.name, "context_length": m.context_length}
                         for m in cached_models]

        if not models:
            console.print("[red]No hay modelos disponibles[/red]")
            return None

        # Separate free and paid models
        free_models = []
        paid_models = []

        for model in models:
            pricing = model.get("pricing", {})
            
            # Check if model has explicit free_tier flag (AIML API)
            if "free_tier" in pricing:
                is_free = pricing.get("free_tier", False)
            else:
                # Standard pricing check (OpenRouter, etc.)
                prompt_price = pricing.get("prompt", "0")
                completion_price = pricing.get("completion", "0")
                
                is_free = (
                    (str(prompt_price) == "0" or prompt_price == 0) and
                    (str(completion_price) == "0" or completion_price == 0)
                )

            if is_free:
                free_models.append(model)
            else:
                paid_models.append(model)

        # Show info note for AIML API
        if provider_name == "aiml":
            console.print(
                "\n[dim]💡 Nota: AIML API usa créditos. Cuenta FREE incluye 50,000 créditos de bono. "
                "Los modelos marcados como FREE son ideales para free tier. "
                "Los modelos marcados como CREDITS consumen más créditos y pueden requerir plan de pago.[/dim]\n"
            )

        # Show free models first if available
        if free_models:
            console.print(f"\n[bold green]🆓 Modelos Gratuitos ({len(free_models)}):[/bold green]\n")
            _display_model_table(free_models[:20], start_num=1)  # Limit to 20

        if paid_models:
            console.print(f"\n[bold yellow]💰 Modelos de Pago ({len(paid_models)}):[/bold yellow]\n")
            offset = len(free_models[:20]) if free_models else 0
            _display_model_table(paid_models[:30], start_num=offset + 1)  # Limit to 30

        # Combine for selection
        all_shown = (free_models[:20] if free_models else []) + (paid_models[:30] if paid_models else [])

        if not all_shown:
            console.print("[yellow]No hay modelos para mostrar[/yellow]")
            return None

        console.print()
        choice = Prompt.ask(
            "Selecciona modelo (o Enter para cancelar)",
            default=""
        )

        if not choice:
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(all_shown):
                selected = all_shown[idx]
                model_id = selected["id"]

                # Update provider config with selected model
                provider_config = config_manager.get_provider_config(provider_name)
                if provider_config:
                    provider_config.default_model = model_id
                    config_manager.save()

                console.print(f"\n[green]✅ Modelo seleccionado: {model_id}[/green]")
                return model_id
            else:
                console.print("[red]Número inválido[/red]")
                return None
        except ValueError:
            # Maybe they typed a model name directly
            for m in all_shown:
                if choice.lower() in m["id"].lower():
                    model_id = m["id"]
                    provider_config = config_manager.get_provider_config(provider_name)
                    if provider_config:
                        provider_config.default_model = model_id
                        config_manager.save()
                    console.print(f"\n[green]✅ Modelo seleccionado: {model_id}[/green]")
                    return model_id

            console.print("[red]Modelo no encontrado[/red]")
            return None

    except Exception as e:
        console.print(f"[red]Error obteniendo modelos: {e}[/red]")
        return None


def _fetch_models_sync(provider_name: str) -> List[Dict[str, Any]]:
    """Fetch models from provider API synchronously.

    Args:
        provider_name: Provider name

    Returns:
        List of model dictionaries
    """
    config_manager = get_multi_provider_config_manager()
    provider_config = config_manager.get_provider_config(provider_name)

    if not provider_config:
        return []

    api_key = config_manager.get_provider_api_key(provider_name)
    if not api_key:
        return []

    # Import provider class
    try:
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

        provider_class = provider_classes.get(provider_name)
        if not provider_class:
            return []

        provider = provider_class(
            api_key=api_key,
            model=provider_config.default_model or "",
            base_url=provider_config.base_url
        )

        # Run async method synchronously
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # Create new loop if current is running
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, provider.list_available_models())
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(provider.list_available_models())

    except Exception as e:
        console.print(f"[dim]Debug: {e}[/dim]")
        # Try fallback
        try:
            return provider.get_fallback_models()
        except:
            return []


def _display_model_table(models: List[Dict[str, Any]], start_num: int = 1):
    """Display models in a table.

    Args:
        models: List of model dictionaries
        start_num: Starting number for model indices
    """
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("ID del Modelo", style="cyan", width=40)
    table.add_column("Contexto", justify="right", width=10)
    table.add_column("Precio", justify="right", width=15)

    for i, model in enumerate(models, start_num):
        model_id = model.get("id", "unknown")
        context = model.get("context_length", 0)
        context_str = f"{context:,}" if context else "-"

        # Format pricing
        pricing = model.get("pricing", {})
        
        # Check for AIML free_tier flag first
        if "free_tier" in pricing:
            is_free = pricing.get("free_tier", False)
            price_str = "[green]FREE[/green]" if is_free else "[yellow]CREDITS[/yellow]"
        else:
            # Standard pricing format (OpenRouter, etc.)
            prompt_price = pricing.get("prompt", "0")
            try:
                price_float = float(prompt_price)
                if price_float == 0:
                    price_str = "[green]FREE[/green]"
                else:
                    # Price per million tokens
                    price_str = f"${price_float * 1000000:.2f}/M"
            except:
                price_str = "-"

        table.add_row(str(i), model_id, context_str, price_str)

    console.print(table)


# Alias functions for backward compatibility
def configure_provider(provider: Optional[str] = None) -> bool:
    """Alias for configure_api_command."""
    return configure_api_command(provider)


def list_providers() -> bool:
    """Alias for status_command."""
    return status_command()
