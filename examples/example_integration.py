#!/usr/bin/env python3
"""Example integration of Sprint 4.2 & 4.3 with existing IABuilder code.

This shows how to integrate the multi-provider config and model registry
with the existing main.py and provider system.
"""

import asyncio
from pathlib import Path

# New multi-provider imports
from iabuilder.config import (
    get_multi_provider_config_manager,
    get_model_registry,
)
from iabuilder.providers import (
    GroqProvider,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    OpenRouterProvider,
)

from rich.console import Console
from rich.panel import Panel

console = Console()


def example_basic_setup():
    """Example 1: Basic multi-provider setup."""
    console.print("\n[bold cyan]Example 1: Basic Multi-Provider Setup[/bold cyan]\n")

    # Get config manager
    config_mgr = get_multi_provider_config_manager()

    # Check if providers are configured
    providers = config_mgr.list_providers()

    if not providers:
        console.print("[yellow]No providers configured. Let's add one...[/yellow]")

        # For demo, add a test provider (in real usage, use /configure-api command)
        config_mgr.add_provider(
            name="groq",
            api_key="gsk_test_key_demo",  # Replace with real key
            default_model="llama-3.3-70b-versatile",
            set_active=True
        )
        console.print("[green]Added Groq provider[/green]")

    # Get active provider
    active = config_mgr.get_active_provider()
    if active:
        console.print(f"[green]Active provider: {active.name}[/green]")
        console.print(f"[dim]Default model: {active.default_model}[/dim]")


def example_create_provider_instance():
    """Example 2: Create provider instance from config."""
    console.print("\n[bold cyan]Example 2: Create Provider Instance[/bold cyan]\n")

    config_mgr = get_multi_provider_config_manager()

    # Get active provider config
    provider_config = config_mgr.get_active_provider()

    if not provider_config:
        console.print("[red]No active provider configured[/red]")
        return

    # Map provider names to classes
    provider_classes = {
        'groq': GroqProvider,
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'google': GoogleProvider,
        'openrouter': OpenRouterProvider,
    }

    # Get API key (checks environment override)
    api_key = config_mgr.get_provider_api_key(provider_config.name)

    # Create provider instance
    provider_class = provider_classes.get(provider_config.name)
    if provider_class:
        provider = provider_class(
            api_key=api_key,
            model=provider_config.default_model or "",
            base_url=provider_config.base_url
        )

        console.print(f"[green]Created {provider.provider_name} provider instance[/green]")
        console.print(f"[dim]Model: {provider.get_current_model()}[/dim]")

        # Now you can use provider for chat, etc.
        # response = await provider.chat_completion(messages=[...])


async def example_refresh_models():
    """Example 3: Refresh model cache from all providers."""
    console.print("\n[bold cyan]Example 3: Refresh Model Cache[/bold cyan]\n")

    registry = get_model_registry()

    console.print("[yellow]Refreshing models from all providers...[/yellow]")

    # This will fetch models from all configured providers
    results = await registry.refresh_models()

    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"  Success: {results['success']}")
    console.print(f"  Refreshed: {', '.join(results['providers_refreshed']) or 'None'}")
    console.print(f"  Failed: {', '.join(results['providers_failed']) or 'None'}")
    console.print(f"  Total models: {results['total_models']}")

    if results['errors']:
        console.print("\n[yellow]Errors:[/yellow]")
        for provider, error in results['errors'].items():
            console.print(f"  {provider}: {error}")


def example_get_models():
    """Example 4: Get and display models."""
    console.print("\n[bold cyan]Example 4: Get Available Models[/bold cyan]\n")

    registry = get_model_registry()

    # Get all models
    all_models = registry.get_available_models()
    console.print(f"[green]Total models cached: {len(all_models)}[/green]")

    # Get models by provider
    config_mgr = get_multi_provider_config_manager()
    active = config_mgr.get_active_provider()

    if active:
        provider_models = registry.get_available_models(provider=active.name)
        console.print(f"[green]Models for {active.name}: {len(provider_models)}[/green]")

        # Show first 5 models
        for model in provider_models[:5]:
            console.print(f"  - {model.id} ({model.context_length:,} tokens)")


def example_search_models():
    """Example 5: Search for models."""
    console.print("\n[bold cyan]Example 5: Search Models[/bold cyan]\n")

    registry = get_model_registry()

    # Search for GPT models
    gpt_models = registry.search_models("gpt")
    console.print(f"[green]Models matching 'gpt': {len(gpt_models)}[/green]")
    for model in gpt_models[:3]:
        console.print(f"  - {model.id} ({model.provider})")

    # Search for vision models
    vision_models = registry.get_available_models(category="vision")
    console.print(f"\n[green]Vision models: {len(vision_models)}[/green]")
    for model in vision_models[:3]:
        console.print(f"  - {model.id} ({model.provider})")


def example_switch_provider():
    """Example 6: Switch between providers."""
    console.print("\n[bold cyan]Example 6: Switch Providers[/bold cyan]\n")

    config_mgr = get_multi_provider_config_manager()

    # List available providers
    providers = config_mgr.list_providers()
    console.print(f"[green]Available providers: {', '.join(providers.keys())}[/green]")

    # Get current active
    active = config_mgr.get_active_provider()
    if active:
        console.print(f"[yellow]Current: {active.name}[/yellow]")

        # Switch to different provider (if available)
        other_providers = [p for p in providers.keys() if p != active.name]
        if other_providers:
            new_provider = other_providers[0]
            config_mgr.set_active_provider(new_provider)
            console.print(f"[green]Switched to: {new_provider}[/green]")

            # Get models for new provider
            registry = get_model_registry()
            models = registry.get_available_models(provider=new_provider)
            console.print(f"[dim]Available models: {len(models)}[/dim]")


def example_model_info():
    """Example 7: Get detailed model information."""
    console.print("\n[bold cyan]Example 7: Model Information[/bold cyan]\n")

    registry = get_model_registry()
    config_mgr = get_multi_provider_config_manager()

    # Get active provider's default model
    active = config_mgr.get_active_provider()
    if active and active.default_model:
        model_info = registry.get_model_info(active.default_model)

        if model_info:
            console.print(
                Panel.fit(
                    f"[bold]ID:[/bold] {model_info.id}\n"
                    f"[bold]Provider:[/bold] {model_info.provider}\n"
                    f"[bold]Name:[/bold] {model_info.name}\n"
                    f"[bold]Context:[/bold] {model_info.context_length:,} tokens\n"
                    f"[bold]Functions:[/bold] {'Yes' if model_info.supports_function_calling else 'No'}\n"
                    f"[bold]Category:[/bold] {model_info.category}\n"
                    f"[bold]Description:[/bold] {model_info.description}",
                    title="Current Model Details",
                    border_style="cyan",
                )
            )
        else:
            console.print(f"[yellow]Model '{active.default_model}' not in cache[/yellow]")
            console.print("[dim]Run /refresh to update cache[/dim]")


def example_integration_with_chat():
    """Example 8: Complete integration for chat."""
    console.print("\n[bold cyan]Example 8: Integration with Chat[/bold cyan]\n")

    config_mgr = get_multi_provider_config_manager()
    registry = get_model_registry()

    # Get active provider
    provider_config = config_mgr.get_active_provider()
    if not provider_config:
        console.print("[red]No active provider configured[/red]")
        console.print("[dim]Use /configure-api to set up a provider[/dim]")
        return

    console.print(f"[green]Provider: {provider_config.name}[/green]")

    # Get model info
    model_id = provider_config.default_model
    if model_id:
        model_info = registry.get_model_info(model_id)
        if model_info:
            console.print(f"[green]Model: {model_info.id}[/green]")
            console.print(f"[dim]Context: {model_info.context_length:,} tokens[/dim]")
            console.print(f"[dim]Functions: {'Yes' if model_info.supports_function_calling else 'No'}[/dim]")

    # Create provider instance
    provider_classes = {
        'groq': GroqProvider,
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'google': GoogleProvider,
        'openrouter': OpenRouterProvider,
    }

    api_key = config_mgr.get_provider_api_key(provider_config.name)
    provider_class = provider_classes.get(provider_config.name)

    if provider_class:
        provider = provider_class(
            api_key=api_key,
            model=model_id or "",
            base_url=provider_config.base_url
        )

        console.print(f"\n[green]Ready to chat with {provider.provider_name}![/green]")

        # Now you can use provider for chat:
        # messages = [{"role": "user", "content": "Hello!"}]
        # response = await provider.chat_completion(messages)
    else:
        console.print(f"[red]Provider class not found for '{provider_config.name}'[/red]")


def main():
    """Run all examples."""
    console.print(
        Panel.fit(
            "[bold cyan]IABuilder Multi-Provider Integration Examples[/bold cyan]\n\n"
            "Demonstrating Sprint 4.2 & 4.3 integration",
            title="Integration Examples",
            border_style="cyan",
        )
    )

    # Run synchronous examples
    example_basic_setup()
    example_create_provider_instance()
    example_get_models()
    example_search_models()
    example_switch_provider()
    example_model_info()
    example_integration_with_chat()

    # Run async examples
    console.print("\n[bold cyan]Running async examples...[/bold cyan]")
    asyncio.run(example_refresh_models())

    # Summary
    console.print(
        "\n" + Panel.fit(
            "[bold green]Examples Complete![/bold green]\n\n"
            "These examples show how to integrate the new multi-provider\n"
            "system with your existing IABuilder code.\n\n"
            "[bold]Key Integration Points:[/bold]\n"
            "1. Use get_multi_provider_config_manager() for config\n"
            "2. Use get_model_registry() for model info\n"
            "3. Create provider instances from config\n"
            "4. Check model capabilities before using\n"
            "5. Handle provider switching dynamically",
            title="Summary",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
