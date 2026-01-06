"""Interactive startup menu for IABuilder.

This module provides interactive menus for selecting API providers and models
at startup. Works with all configured providers (Groq, OpenAI, Anthropic, etc.)
"""

import asyncio
from typing import Optional, Tuple, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config.provider_config import get_multi_provider_config_manager, ProviderConfig
from ..config.model_registry import get_model_registry, ModelInfo
from ..config.model_capabilities import (
    get_model_capability,
    get_models_by_provider,
    PricingTier,
    ModelCapability,
)


console = Console()


class StartupMenu:
    """Interactive menu system for startup configuration."""

    def __init__(self):
        """Initialize startup menu."""
        self.provider_manager = get_multi_provider_config_manager()
        self.model_registry = get_model_registry()

    def show_welcome_banner(self):
        """Show welcome banner with provider selection."""
        console.print()
        console.print(Panel.fit(
            "[bold cyan]Bienvenido a IABuilder[/bold cyan]\n"
            "[dim]Multi-Provider AI Development Tool[/dim]",
            border_style="cyan"
        ))
        console.print()

    def _show_initial_setup_menu(self) -> Optional[ProviderConfig]:
        """Show initial setup menu when no providers are configured.

        Returns:
            Configured ProviderConfig or None if cancelled
        """
        console.print(Panel.fit(
            "[bold yellow]⚠️  No hay proveedores de API configurados[/bold yellow]\n\n"
            "[dim]Necesitas configurar al menos un proveedor para usar IABuilder.[/dim]",
            border_style="yellow"
        ))
        console.print()

        # Available providers with descriptions
        provider_options = [
            ("groq", "Groq Cloud", "🆓 Gratis, muy rápido (Llama, Qwen, Mistral)", "https://console.groq.com/keys"),
            ("google", "Google AI", "🆓 Gratis con límites (Gemini 2.0)", "https://aistudio.google.com/apikey"),
            ("openrouter", "OpenRouter", "💰 Gateway a múltiples modelos", "https://openrouter.ai/keys"),
            ("openai", "OpenAI", "💰 De pago (GPT-4, o1)", "https://platform.openai.com/api-keys"),
            ("anthropic", "Anthropic", "💰 De pago (Claude)", "https://console.anthropic.com/"),
            ("ollama", "Ollama (Local)", "🖥️  Modelos locales, sin internet", "http://localhost:11434"),
        ]

        # Show options table
        console.print("[bold]🔧 Selecciona un proveedor para configurar:[/bold]\n")

        table = Table(show_header=True, header_style="bold cyan", border_style="dim")
        table.add_column("#", style="cyan", width=3, justify="right")
        table.add_column("Proveedor", style="green", width=18)
        table.add_column("Descripción", style="white", width=40)

        for idx, (key, name, desc, url) in enumerate(provider_options, 1):
            table.add_row(str(idx), name, desc)

        console.print(table)
        console.print()
        console.print("[dim]0. Salir sin configurar[/dim]\n")

        try:
            choice = IntPrompt.ask(
                "Selecciona una opción",
                default=1,
                console=console
            )

            if choice == 0:
                console.print("[yellow]Saliendo sin configurar...[/yellow]")
                return None

            if choice < 1 or choice > len(provider_options):
                console.print("[red]Opción inválida[/red]")
                return None

            provider_key, provider_name, desc, url = provider_options[choice - 1]

            # Handle Ollama (local) differently
            if provider_key == "ollama":
                return self._configure_ollama()

            # Configure cloud provider
            return self._configure_cloud_provider(provider_key, provider_name, url)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Configuración cancelada[/yellow]")
            return None

    def _configure_cloud_provider(self, provider_key: str, provider_name: str, url: str) -> Optional[ProviderConfig]:
        """Configure a cloud API provider.

        Args:
            provider_key: Provider identifier (groq, openai, etc.)
            provider_name: Display name
            url: URL to get API key

        Returns:
            Configured ProviderConfig or None
        """
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]Configurar {provider_name}[/bold cyan]\n\n"
            f"[dim]Obtén tu API key en:[/dim]\n"
            f"[link={url}]{url}[/link]",
            border_style="cyan"
        ))
        console.print()

        try:
            api_key = Prompt.ask(f"Ingresa tu API key de {provider_name}").strip()

            if not api_key:
                console.print("[red]API key no puede estar vacía[/red]")
                return None

            # Add provider
            self.provider_manager.add_provider(
                name=provider_key,
                api_key=api_key,
                set_active=True
            )

            console.print(f"\n[green]✅ {provider_name} configurado correctamente![/green]")

            # Return the configured provider
            return self.provider_manager.get_active_provider()

        except Exception as e:
            console.print(f"[red]Error al configurar: {e}[/red]")
            return None

    def _configure_ollama(self) -> Optional[ProviderConfig]:
        """Configure Ollama for local model inference.

        Returns:
            Configured ProviderConfig or None
        """
        console.print()
        console.print(Panel.fit(
            "[bold cyan]Configurar Ollama (Modelos Locales)[/bold cyan]\n\n"
            "[dim]Ollama permite ejecutar modelos de IA en tu computadora.[/dim]\n\n"
            "Requisitos:\n"
            "• Ollama instalado: [link=https://ollama.ai]https://ollama.ai[/link]\n"
            "• Al menos un modelo descargado (ej: ollama pull llama3.2)",
            border_style="cyan"
        ))
        console.print()

        # Check if Ollama is running
        import subprocess
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                raise Exception("Ollama not responding")

            console.print("[green]✅ Ollama está ejecutándose[/green]\n")

            # Parse available models
            import json
            try:
                data = json.loads(result.stdout)
                models = [m.get("name", "") for m in data.get("models", [])]
                if models:
                    console.print("[bold]Modelos disponibles:[/bold]")
                    for m in models[:10]:  # Show max 10
                        console.print(f"  • {m}")
                    console.print()
            except:
                pass

        except Exception as e:
            console.print("[yellow]⚠️  No se pudo conectar con Ollama[/yellow]")
            console.print("[dim]Asegúrate de que Ollama esté instalado y ejecutándose:[/dim]")
            console.print("[dim]  1. Instalar: curl -fsSL https://ollama.ai/install.sh | sh[/dim]")
            console.print("[dim]  2. Iniciar: ollama serve[/dim]")
            console.print("[dim]  3. Descargar modelo: ollama pull llama3.2[/dim]\n")

            if not Confirm.ask("¿Continuar de todos modos?", default=False):
                return None

        # Get base URL
        base_url = Prompt.ask(
            "URL de Ollama",
            default="http://localhost:11434"
        ).strip()

        # Get default model
        default_model = Prompt.ask(
            "Modelo por defecto",
            default="llama3.2"
        ).strip()

        try:
            # Add Ollama as provider
            self.provider_manager.add_provider(
                name="ollama",
                api_key="ollama",  # Ollama doesn't need API key
                base_url=f"{base_url}/v1",
                default_model=default_model,
                set_active=True
            )

            console.print(f"\n[green]✅ Ollama configurado con modelo {default_model}![/green]")
            return self.provider_manager.get_active_provider()

        except Exception as e:
            console.print(f"[red]Error al configurar Ollama: {e}[/red]")
            return None

    def select_provider(self) -> Optional[ProviderConfig]:
        """Show interactive provider selection menu.

        Returns:
            Selected ProviderConfig or None if cancelled
        """
        # Get enabled providers
        providers = self.provider_manager.list_providers(enabled_only=True)

        if not providers:
            # No providers configured - show setup menu
            return self._show_initial_setup_menu()

        # Show providers table
        console.print("[bold]📡 APIs Configuradas:[/bold]\n")

        table = Table(show_header=True, header_style="bold cyan", border_style="dim")
        table.add_column("#", style="cyan", width=3, justify="right")
        table.add_column("Proveedor", style="green", width=15)
        table.add_column("Modelo por Defecto", style="yellow", width=30)
        table.add_column("Estado", style="magenta", width=10, justify="center")

        provider_list = []
        for idx, (name, config) in enumerate(sorted(providers.items()), 1):
            provider_list.append((name, config))

            # Format default model
            default_model = config.default_model or "[dim]No configurado[/dim]"

            # Status indicator
            active_provider = self.provider_manager.get_active_provider()
            status = "✅ Activo" if active_provider and name == active_provider.name else "⚪"

            table.add_row(
                str(idx),
                name.upper(),
                default_model,
                status
            )

        console.print(table)
        console.print()

        # Prompt for selection
        try:
            choice = IntPrompt.ask(
                "Selecciona un proveedor",
                default=1,
                show_default=True,
                console=console
            )

            if choice < 1 or choice > len(provider_list):
                console.print("[red]Opción inválida[/red]")
                return None

            selected_name, selected_config = provider_list[choice - 1]

            # Set as active provider
            self.provider_manager.set_active_provider(selected_name)

            console.print(f"[green]✅ Proveedor seleccionado: {selected_name.upper()}[/green]\n")

            return selected_config

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Selección cancelada[/yellow]")
            return None

    async def fetch_models_async(self, provider_name: str) -> Tuple[bool, list]:
        """Fetch models from provider asynchronously.

        Args:
            provider_name: Name of the provider

        Returns:
            Tuple of (success, models_list)
        """
        try:
            results = await self.model_registry.refresh_models(provider_name)

            if results['success'] and results['providers_refreshed']:
                models = self.model_registry.get_available_models(provider=provider_name)
                return True, models
            else:
                # Return error info
                error_msg = results['errors'].get(provider_name, "Unknown error")
                return False, [error_msg]

        except Exception as e:
            return False, [str(e)]

    def _get_capability_info(self, model_id: str, provider_name: str) -> Optional[ModelCapability]:
        """Get capability info for a model, trying multiple ID formats."""
        # Direct lookup
        cap = get_model_capability(model_id)
        if cap:
            return cap

        # Try with provider prefix
        cap = get_model_capability(f"{provider_name}/{model_id}")
        if cap:
            return cap

        # Try without provider prefix
        if "/" in model_id:
            cap = get_model_capability(model_id.split("/")[-1])
            if cap:
                return cap

        return None

    def _format_rating(self, rating: int) -> str:
        """Format dev rating as stars."""
        return "⭐" * rating + "☆" * (5 - rating)

    def _format_tier(self, tier: PricingTier) -> str:
        """Format pricing tier indicator."""
        if tier == PricingTier.FREE:
            return "[green]🆓 FREE[/green]"
        elif tier == PricingTier.PREMIUM:
            return "[red]💎 PREMIUM[/red]"
        else:
            return "[yellow]💰 PAID[/yellow]"

    def select_model(self, provider_name: str, provider_config: ProviderConfig) -> Optional[str]:
        """Show interactive model selection menu.

        Args:
            provider_name: Name of the selected provider
            provider_config: Provider configuration

        Returns:
            Selected model ID or None if cancelled
        """
        console.print(f"[bold]🤖 Modelos Disponibles para {provider_name.upper()}:[/bold]\n")

        # Show loading spinner while fetching models
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Consultando modelos de {provider_name.upper()}...",
                total=None
            )

            # Run async fetch
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            success, result = loop.run_until_complete(
                self.fetch_models_async(provider_name)
            )

        console.print()

        if not success:
            console.print(f"[red]❌ Error al consultar modelos: {result[0]}[/red]")
            console.print("[yellow]Usando modelo por defecto si está configurado...[/yellow]\n")
            return provider_config.default_model

        models = result

        if not models:
            console.print("[yellow]⚠️  No se encontraron modelos para este proveedor[/yellow]")
            console.print("[dim]Usando modelo por defecto...[/dim]\n")
            return provider_config.default_model

        # For OpenRouter: Ask if user wants to filter free models only
        filter_free = False
        if provider_name.lower() == "openrouter":
            # Count free models
            free_count = sum(1 for m in models if getattr(m, 'is_free', False) or ":free" in m.id.lower())
            total_count = len(models)

            if free_count > 0 and free_count < total_count:
                console.print(f"[dim]Se encontraron {total_count} modelos ({free_count} gratuitos)[/dim]")
                filter_free = Confirm.ask(
                    "¿Mostrar solo modelos gratuitos?",
                    default=True
                )
                console.print()

                if filter_free:
                    models = [m for m in models if getattr(m, 'is_free', False) or ":free" in m.id.lower()]
                    console.print(f"[green]✓ Mostrando {len(models)} modelos gratuitos[/green]\n")

        # Create models table with enhanced info
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
            box=None,  # No borders for cleaner look
            padding=(0, 1),
        )
        table.add_column("#", style="cyan", width=3, justify="right")
        table.add_column("Modelo", style="yellow", no_wrap=False, max_width=70)
        table.add_column("Rating", width=11, justify="center")
        table.add_column("Tier", width=10, justify="center")
        table.add_column("Ctx", style="green", width=5, justify="right")
        table.add_column("🔧", width=2, justify="center")
        table.add_column("Mejor para", style="dim")

        # Sort models: by capability rating first (if available), then by context window
        def sort_key(m):
            cap = self._get_capability_info(m.id, provider_name)
            if cap:
                return (-cap.dev_rating, -cap.context_window, m.id)
            return (0, -m.context_length if m.context_length > 0 else 0, m.id)

        models_sorted = sorted(models, key=sort_key)

        for idx, model in enumerate(models_sorted, 1):
            # Get capability info
            cap = self._get_capability_info(model.id, provider_name)

            # Format context length
            context_len = cap.context_window if cap else model.context_length
            if context_len >= 1000000:
                context = f"{context_len // 1000000}M"
            elif context_len > 0:
                context = f"{context_len // 1000}K"
            else:
                context = "-"

            # Function calling indicator
            supports_tools = cap.supports_tools if cap else model.supports_function_calling
            tools_icon = "✅" if supports_tools else "❌"

            # Rating and tier (from capabilities)
            if cap:
                rating = self._format_rating(cap.dev_rating)
                tier = self._format_tier(cap.tier)
                best_for = ", ".join(cap.best_for[:2]) if cap.best_for else ""
            else:
                rating = "[dim]- - -[/dim]"
                tier = "[dim]?[/dim]"
                best_for = model.description[:22] + "..." if len(model.description) > 22 else model.description

            # Highlight if it's the current default
            model_id_display = model.id
            if model.id == provider_config.default_model:
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

        console.print(table)
        console.print()

        # Show legend
        console.print("[dim]Leyenda: ⭐=Rating desarrollo | 🆓=Gratis 💰=Pago 💎=Premium | ✅=Soporta herramientas[/dim]")
        console.print(f"[dim]Total: {len(models)} modelos disponibles[/dim]\n")

        # Prompt for selection
        try:
            # Find default index
            default_idx = 1
            if provider_config.default_model:
                for idx, model in enumerate(models_sorted, 1):
                    if model.id == provider_config.default_model:
                        default_idx = idx
                        break

            choice = IntPrompt.ask(
                "Selecciona un modelo",
                default=default_idx,
                show_default=True,
                console=console
            )

            if choice < 1 or choice > len(models_sorted):
                console.print("[red]Opción inválida[/red]")
                return provider_config.default_model

            selected_model = models_sorted[choice - 1]

            # Update provider's default model
            provider_config.default_model = selected_model.id
            self.provider_manager._save_registry()

            console.print(f"\n[green]✅ Modelo seleccionado: {selected_model.id}[/green]")

            # Show enhanced model details from capabilities
            cap = self._get_capability_info(selected_model.id, provider_name)
            if cap:
                console.print(f"   [cyan]Rating:[/cyan] {self._format_rating(cap.dev_rating)}")
                console.print(f"   [cyan]Contexto:[/cyan] {cap.context_window:,} tokens")
                console.print(f"   [cyan]Herramientas:[/cyan] {'Sí' if cap.supports_tools else 'No'} | Paralelas: {'Sí' if cap.supports_parallel_tools else 'No'}")
                console.print(f"   [cyan]Visión:[/cyan] {'Sí' if cap.supports_vision else 'No'}")
                if cap.best_for:
                    console.print(f"   [cyan]Mejor para:[/cyan] {', '.join(cap.best_for)}")
                if cap.notes:
                    console.print(f"   [dim]{cap.notes}[/dim]")

                # Warning for models without tool support
                if not cap.supports_tools:
                    console.print("\n[yellow]⚠️  ADVERTENCIA: Este modelo NO soporta herramientas/funciones.[/yellow]")
                    console.print("[yellow]   Las capacidades de desarrollo serán limitadas.[/yellow]")
            else:
                console.print(f"   [cyan]Contexto:[/cyan] {selected_model.context_length:,} tokens")
                console.print(f"   [cyan]Funciones:[/cyan] {'Sí' if selected_model.supports_function_calling else 'No'}")

            console.print()

            return selected_model.id, cap.supports_tools if cap else selected_model.supports_function_calling

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Selección cancelada, usando modelo por defecto[/yellow]")
            return provider_config.default_model, False

    def select_toolbox_mode(self, model_supports_tools: bool) -> bool:
        """Ask user if they want to enable toolbox (tools/function calling).

        Args:
            model_supports_tools: Whether the selected model supports tools

        Returns:
            True if toolbox should be enabled, False otherwise
        """
        console.print()

        if not model_supports_tools:
            console.print(Panel.fit(
                "[bold yellow]⚠️  Toolbox Deshabilitado[/bold yellow]\n\n"
                "[dim]El modelo seleccionado NO soporta herramientas.\n"
                "IABuilder funcionará en modo chat solamente.[/dim]",
                border_style="yellow"
            ))
            return False

        # Model supports tools - ask user
        console.print(Panel.fit(
            "[bold cyan]🧰 Configuración de Toolbox[/bold cyan]\n\n"
            "[green]ON[/green]  = El modelo puede ejecutar comandos, leer/escribir archivos, buscar en internet\n"
            "[yellow]OFF[/yellow] = Solo chat de texto (más rápido, menos tokens)",
            border_style="cyan"
        ))
        console.print()

        try:
            enable_tools = Confirm.ask(
                "¿Activar Toolbox (herramientas)?",
                default=True,
                console=console
            )

            if enable_tools:
                console.print("[green]✅ Toolbox: ON - Herramientas habilitadas[/green]")
            else:
                console.print("[yellow]⚡ Toolbox: OFF - Modo chat rápido[/yellow]")

            return enable_tools

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Usando Toolbox: ON por defecto[/yellow]")
            return True

    def run(self, skip_if_configured: bool = False) -> Tuple[Optional[str], Optional[str], bool]:
        """Run the complete startup menu flow.

        Args:
            skip_if_configured: If True, skip menu if provider is already configured

        Returns:
            Tuple of (provider_name, model_id, toolbox_enabled) or (None, None, False) if cancelled
        """
        # Check if we should skip
        if skip_if_configured:
            active_provider = self.provider_manager.get_active_provider()
            if active_provider and active_provider.default_model:
                # Load toolbox setting from config
                from ..config.config import get_config_manager
                config = get_config_manager().load()
                return active_provider.name, active_provider.default_model, getattr(config, 'toolbox', True)

        # Show welcome banner
        self.show_welcome_banner()

        # Step 1: Select provider
        provider_config = self.select_provider()
        if not provider_config:
            return None, None, False

        active_provider = self.provider_manager.get_active_provider()
        provider_name = active_provider.name if active_provider else None

        # Step 2: Select model
        result = self.select_model(provider_name, provider_config)
        if isinstance(result, tuple):
            model_id, model_supports_tools = result
        else:
            model_id = result
            model_supports_tools = False

        if not model_id:
            return provider_name, None, False

        # Step 3: Select toolbox mode
        toolbox_enabled = self.select_toolbox_mode(model_supports_tools)

        # Save toolbox setting to config
        from ..config.config import get_config_manager
        config_manager = get_config_manager()
        config = config_manager.load()
        config.toolbox = toolbox_enabled
        config_manager.save(config)

        # Show final summary
        toolbox_status = "[green]ON 🧰[/green]" if toolbox_enabled else "[yellow]OFF ⚡[/yellow]"
        console.print(Panel.fit(
            f"[bold green]Configuración Completada[/bold green]\n\n"
            f"[cyan]Proveedor:[/cyan] {provider_name.upper()}\n"
            f"[cyan]Modelo:[/cyan] {model_id}\n"
            f"[cyan]Toolbox:[/cyan] {toolbox_status}\n\n"
            f"[dim]El asistente está listo para usar este modelo[/dim]",
            border_style="green"
        ))
        console.print()

        return provider_name, model_id, toolbox_enabled


def show_startup_menu(skip_if_configured: bool = False) -> Tuple[Optional[str], Optional[str], bool]:
    """Show startup menu and return selected configuration.

    Args:
        skip_if_configured: If True, skip menu if provider is already configured

    Returns:
        Tuple of (provider_name, model_id, toolbox_enabled) or (None, None, False) if cancelled
    """
    menu = StartupMenu()
    return menu.run(skip_if_configured=skip_if_configured)
