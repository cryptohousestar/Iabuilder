"""Model management commands for IABuilder.

Commands for listing, switching, and managing models from multiple providers.
"""

import asyncio
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config.model_registry import get_model_registry
from ..config.provider_config import get_multi_provider_config_manager
from ..config.model_capabilities import (
    get_model_capability,
    PricingTier,
    ModelCapability,
)


console = Console()


def _get_capability_info(model_id: str, provider_name: str) -> Optional[ModelCapability]:
    """Get capability info for a model, trying multiple ID formats."""
    cap = get_model_capability(model_id)
    if cap:
        return cap
    cap = get_model_capability(f"{provider_name}/{model_id}")
    if cap:
        return cap
    if "/" in model_id:
        cap = get_model_capability(model_id.split("/")[-1])
        if cap:
            return cap
    return None


def _format_rating(rating: int) -> str:
    """Format dev rating as stars."""
    return "⭐" * rating + "☆" * (5 - rating)


def _format_tier(tier: PricingTier) -> str:
    """Format pricing tier indicator."""
    if tier == PricingTier.FREE:
        return "[green]🆓 FREE[/green]"
    elif tier == PricingTier.PREMIUM:
        return "[red]💎 PREMIUM[/red]"
    else:
        return "[yellow]💰 PAID[/yellow]"


def models_command(provider: Optional[str] = None) -> bool:
    """List available models from cache.

    Usage:
        /models              # List all models from all providers
        /models groq         # List only Groq models
        /models openai       # List only OpenAI models

    Args:
        provider: Optional provider filter

    Returns:
        True if successful, False otherwise
    """
    registry = get_model_registry()

    # Get models
    models = registry.get_available_models(provider=provider)

    if not models:
        if provider:
            console.print(f"[yellow]No models found for provider '{provider}'[/yellow]")
        else:
            console.print("[yellow]No models cached[/yellow]")
        console.print("[dim]Use /refresh to fetch models from providers[/dim]")
        return True

    # Group by provider
    models_by_provider = {}
    for model in models:
        if model.provider not in models_by_provider:
            models_by_provider[model.provider] = []
        models_by_provider[model.provider].append(model)

    # Display each provider's models
    for provider_name in sorted(models_by_provider.keys()):
        provider_models = models_by_provider[provider_name]

        # Create table
        table = Table(
            title=f"{provider_name.upper()} Models ({len(provider_models)})",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Model ID", style="cyan", no_wrap=True)
        table.add_column("Context", justify="right", style="yellow")
        table.add_column("Functions", justify="center")
        table.add_column("Category", style="green")
        table.add_column("Description", style="dim")

        # Sort by ID
        provider_models.sort(key=lambda m: m.id)

        for model in provider_models:
            # Format context length
            context = f"{model.context_length:,}" if model.context_length > 0 else "-"

            # Function calling indicator
            functions = "Yes" if model.supports_function_calling else ""

            # Truncate description
            description = model.description[:50] + "..." if len(model.description) > 50 else model.description

            table.add_row(
                model.id,
                context,
                functions,
                model.category,
                description
            )

        console.print()
        console.print(table)

    # Show cache info
    cache_info = registry.get_cache_info()
    console.print()
    console.print(
        f"[dim]Cache: {cache_info['total_models']} models from {len(cache_info['providers'])} providers | "
        f"Last refresh: {cache_info['last_refresh'] or 'Never'} | "
        f"Expired: {'Yes' if cache_info['is_expired'] else 'No'}[/dim]"
    )
    console.print("[dim]Use /refresh to update model list[/dim]")
    console.print()

    return True


def model_command(model_id: Optional[str] = None) -> str:
    """Show model selector or switch to a specific model.

    Usage:
        /model                           # Show interactive model selector
        /model llama-3.3-70b-versatile  # Switch to model
        /model gpt-4                     # Switch to model

    Args:
        model_id: Optional model ID to switch to

    Returns:
        Status message string
    """
    config_manager = get_multi_provider_config_manager()
    registry = get_model_registry()

    # Get active provider
    active_provider = config_manager.get_active_provider()

    if not active_provider:
        console.print("[red]Error: No active provider configured[/red]")
        console.print("[dim]Use /configure-api to set up a provider[/dim]")
        return ""

    # If no model specified, show interactive selector with detailed table
    if not model_id:
        current_model = active_provider.default_model or "Not set"
        provider_name = active_provider.name

        # Get models for current provider
        models = registry.get_available_models(provider=provider_name)

        if not models:
            console.print(f"[yellow]No models cached for {provider_name}[/yellow]")
            console.print("[dim]Use /refresh to fetch models from provider[/dim]")
            return ""

        # Sort models by capability rating, then context window
        def sort_key(m):
            cap = _get_capability_info(m.id, provider_name)
            if cap:
                return (-cap.dev_rating, -cap.context_window, m.id)
            return (0, -m.context_length if m.context_length > 0 else 0, m.id)

        models_sorted = sorted(models, key=sort_key)

        # Create detailed table (same format as startup menu)
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
            box=None,
            padding=(0, 1),
        )
        table.add_column("#", style="cyan", width=4, justify="right")
        table.add_column("Modelo", style="yellow", no_wrap=False, max_width=50)
        table.add_column("Rating", width=11, justify="center")
        table.add_column("Tier", width=12, justify="center")
        table.add_column("Ctx", style="green", width=6, justify="right")
        table.add_column("🔧", width=2, justify="center")
        table.add_column("Mejor para", style="dim", max_width=35)

        for idx, model in enumerate(models_sorted, 1):
            cap = _get_capability_info(model.id, provider_name)

            # Format context length
            context_len = cap.context_window if cap else model.context_length
            if context_len >= 1000000:
                context = f"{context_len // 1000000}M"
            elif context_len > 0:
                context = f"{context_len // 1000}K"
            else:
                context = "-"

            # Tool support
            supports_tools = cap.supports_tools if cap else model.supports_function_calling
            tools_icon = "✅" if supports_tools else "❌"

            # Rating and tier
            if cap:
                rating = _format_rating(cap.dev_rating)
                tier = _format_tier(cap.tier)
                best_for = ", ".join(cap.best_for[:2]) if cap.best_for else ""
            else:
                rating = "[dim]- - -[/dim]"
                tier = "[dim]?[/dim]"
                best_for = model.description[:30] + "..." if len(model.description) > 30 else model.description

            # Highlight current model
            model_id_display = model.id
            if model.id == current_model:
                model_id_display = f"[bold]{model.id}[/bold] ◀"

            table.add_row(
                str(idx),
                model_id_display,
                rating,
                tier,
                context,
                tools_icon,
                best_for
            )

        console.print()
        console.print(f"[bold]🤖 Modelos disponibles para {provider_name.upper()}:[/bold]")
        console.print()
        console.print(table)
        console.print()
        console.print("[dim]Leyenda: ⭐=Rating desarrollo | 🆓=Gratis 💰=Pago 💎=Premium | ✅=Soporta herramientas[/dim]")
        console.print(f"[dim]Total: {len(models_sorted)} modelos disponibles[/dim]")
        console.print()

        # Get user selection
        try:
            # Find default index
            default_idx = 1
            for idx, model in enumerate(models_sorted, 1):
                if model.id == current_model:
                    default_idx = idx
                    break

            choice = IntPrompt.ask(
                "Selecciona un modelo (Enter para cancelar)",
                default=default_idx,
                console=console
            )

            if choice < 1 or choice > len(models_sorted):
                console.print("[red]Opción inválida[/red]")
                return ""

            selected_model = models_sorted[choice - 1]
            # Recursively call with the selected model ID
            return model_command(selected_model.id)

        except (ValueError, KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelado[/dim]")
            return ""

    # Switch to new model
    model_id = model_id.strip()

    # Check if model exists in cache
    model_info = registry.get_model_info(model_id)

    if not model_info:
        console.print(f"[yellow]Warning: Model '{model_id}' not found in cache[/yellow]")
        console.print("[dim]This might be a valid model not yet cached[/dim]")
        if not Confirm.ask("Continue anyway?", default=True):
            return ""
        model_provider = active_provider.name
    else:
        model_provider = model_info.provider

    # Check if we need to switch providers
    if model_provider != active_provider.name:
        console.print(
            f"[yellow]Model '{model_id}' belongs to provider '{model_provider}'[/yellow]"
        )
        if Confirm.ask(f"Switch to provider '{model_provider}'?", default=True):
            if not config_manager.set_active_provider(model_provider):
                console.print(f"[red]Error: Provider '{model_provider}' not configured[/red]")
                return ""
            active_provider = config_manager.get_active_provider()

    # Update default model for provider
    active_provider.default_model = model_id
    config_manager._save_registry()

    console.print(f"[green]Switched to model: {model_id}[/green]")
    if model_info:
        console.print(f"[dim]Context: {model_info.context_length:,} tokens | "
                     f"Functions: {'Yes' if model_info.supports_function_calling else 'No'}[/dim]")

    return f"Switched to model: {model_id}"


def add_model_command() -> bool:
    """Manually add a model to the registry.

    Useful for custom models or providers without model listing support.

    Usage:
        /add-model

    Returns:
        True if successful, False otherwise
    """
    config_manager = get_multi_provider_config_manager()
    registry = get_model_registry()

    console.print("\n[bold cyan]Add Custom Model[/bold cyan]\n")

    # Get provider
    providers = config_manager.list_providers()
    if not providers:
        console.print("[red]Error: No providers configured[/red]")
        console.print("[dim]Use /configure-api to set up a provider first[/dim]")
        return False

    provider_list = list(providers.keys())
    console.print("Available providers:")
    for i, name in enumerate(provider_list, 1):
        console.print(f"  {i}. {name}")
    console.print()

    choice = Prompt.ask(
        "Select provider",
        choices=[str(i) for i in range(1, len(provider_list) + 1)]
    )
    provider = provider_list[int(choice) - 1]

    # Get model details
    model_id = Prompt.ask("Model ID (e.g., 'gpt-4-custom')").strip()
    if not model_id:
        console.print("[red]Error: Model ID cannot be empty[/red]")
        return False

    # Check if exists
    existing = registry.get_model_info(model_id)
    if existing:
        console.print(f"[yellow]Warning: Model '{model_id}' already exists[/yellow]")
        if not Confirm.ask("Overwrite?", default=False):
            return False

    name = Prompt.ask("Display name (press Enter to use ID)", default=model_id).strip()

    context_length_str = Prompt.ask("Context length (tokens)", default="8000").strip()
    try:
        context_length = int(context_length_str)
    except ValueError:
        console.print("[red]Error: Context length must be a number[/red]")
        return False

    supports_functions = Confirm.ask("Supports function calling?", default=True)

    description = Prompt.ask("Description (optional)", default="").strip()

    category = Prompt.ask(
        "Category",
        choices=["llm", "vision", "embedding", "tts", "whisper", "other"],
        default="llm"
    )

    try:
        model_info = registry.add_manual_model(
            model_id=model_id,
            provider=provider,
            name=name,
            context_length=context_length,
            supports_function_calling=supports_functions,
            description=description,
            category=category
        )

        console.print(f"\n[green]Model '{model_id}' added successfully[/green]")

        # Ask if user wants to switch to this model
        if Confirm.ask("Switch to this model now?", default=True):
            model_command(model_id)

        return True

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


def refresh_command(provider: Optional[str] = None) -> bool:
    """Force refresh model cache from provider(s).

    Usage:
        /refresh          # Refresh all providers
        /refresh groq     # Refresh only Groq

    Args:
        provider: Optional provider to refresh

    Returns:
        True if successful, False otherwise
    """
    registry = get_model_registry()
    config_manager = get_multi_provider_config_manager()

    # Get providers to refresh
    if provider:
        providers = {provider: config_manager.get_provider_config(provider)}
        if providers[provider] is None:
            console.print(f"[red]Error: Provider '{provider}' not found[/red]")
            return False
    else:
        providers = config_manager.list_providers(enabled_only=True)

    if not providers:
        console.print("[yellow]No providers configured[/yellow]")
        console.print("[dim]Use /configure-api to add a provider[/dim]")
        return False

    # Run async refresh with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Refreshing models from {len(providers)} provider(s)...",
            total=None
        )

        # Run async refresh
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        results = loop.run_until_complete(registry.refresh_models(provider))

    # Display results
    console.print()

    if results['success']:
        console.print(
            f"[green]Successfully refreshed {len(results['providers_refreshed'])} provider(s)[/green]"
        )
    else:
        console.print("[yellow]Refresh completed with some errors[/yellow]")

    if results['providers_refreshed']:
        console.print(f"[green]Success:[/green] {', '.join(results['providers_refreshed'])}")

    if results['providers_failed']:
        console.print(f"[red]Failed:[/red] {', '.join(results['providers_failed'])}")
        for provider_name, error in results['errors'].items():
            console.print(f"  [red]{provider_name}:[/red] {error}")

    console.print(f"\n[bold]Total models cached:[/bold] {results['total_models']}")

    # Show cache info
    cache_info = registry.get_cache_info()
    console.print(
        f"[dim]Providers: {', '.join(cache_info['providers'])} | "
        f"Last refresh: {cache_info['last_refresh']}[/dim]"
    )
    console.print()

    return True


def search_models_command(query: str, provider: Optional[str] = None) -> bool:
    """Search for models by query.

    Usage:
        /search-models gpt
        /search-models llama openai

    Args:
        query: Search query
        provider: Optional provider filter

    Returns:
        True if successful, False otherwise
    """
    registry = get_model_registry()

    if not query or not query.strip():
        console.print("[red]Error: Search query cannot be empty[/red]")
        return False

    # Search
    models = registry.search_models(query.strip(), provider=provider)

    if not models:
        console.print(f"[yellow]No models found matching '{query}'[/yellow]")
        if provider:
            console.print(f"[dim]In provider: {provider}[/dim]")
        return True

    # Create table
    table = Table(
        title=f"Search Results for '{query}' ({len(models)} found)",
        show_header=True,
        header_style="bold cyan"
    )
    table.add_column("Model ID", style="cyan", no_wrap=True)
    table.add_column("Provider", style="magenta")
    table.add_column("Context", justify="right", style="yellow")
    table.add_column("Functions", justify="center")
    table.add_column("Description", style="dim")

    for model in models:
        # Format context length
        context = f"{model.context_length:,}" if model.context_length > 0 else "-"

        # Function calling indicator
        functions = "Yes" if model.supports_function_calling else ""

        # Truncate description
        description = model.description[:50] + "..." if len(model.description) > 50 else model.description

        table.add_row(
            model.id,
            model.provider,
            context,
            functions,
            description
        )

    console.print()
    console.print(table)
    console.print()

    return True
