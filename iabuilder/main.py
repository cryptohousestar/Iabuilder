"""Main application module for IABuilder - Multi-Provider AI Development Tool."""

import argparse
import sys
import threading
import select
import platform
from pathlib import Path
from typing import Optional
import readchar

# Multi-platform terminal handling
if platform.system() == "Windows":
    import msvcrt
else:
    import termios
    import tty

from .core import AppBootstrap
from .chat import ChatHandler
from .ai import ResponseProcessor, RetryHandler, ToolCallError, get_adapter_for_model
from .errors import get_error_handler
from .tools import setup_tools, get_tool_registry
from .ui import show_startup_menu
from .debug import debug, debug_separator, debug_adapter
from .commands.provider_commands import (
    configure_api_command,
    add_provider_command,
    remove_api_command,
    status_command,
    provider_command,
)
from .commands.model_commands import (
    models_command,
    model_command,
    add_model_command,
    refresh_command,
    search_models_command,
)


class IABuilderApp:
    """Main application class with intelligent tool management."""

    def __init__(self, working_directory: Optional[str] = None):
        """Initialize the application.

        Args:
            working_directory: Directory to work in (defaults to current directory)
        """
        # Initialize error handler
        self.error_handler = get_error_handler()

        # Bootstrap application
        self.bootstrap = AppBootstrap(working_directory)
        self.renderer = self.bootstrap.renderer

        # Show splash screen
        is_first_run = self.bootstrap.show_splash_screen()

        # Initialize configuration
        (
            self.config_manager,
            self.config,
            self.provider_config,
            self.model_registry
        ) = self.bootstrap.initialize_config()

        # Show interactive startup menu for provider and model selection
        provider_name, model_id, toolbox_enabled = show_startup_menu(skip_if_configured=False)

        # Store provider name for rate limiting
        self.current_provider = provider_name or "groq"

        # Store toolbox setting
        self.toolbox_enabled = toolbox_enabled

        # Update config with selected model if menu was completed
        if provider_name and model_id:
            self.config.default_model = model_id

        # Show provider status if not first run
        if not is_first_run:
            self.bootstrap.show_provider_status(self.provider_config)

        # Explore project
        self.project_explorer, self.project_context = self.bootstrap.explore_project()

        # Add toolbox setting to project context for system prompt
        if self.project_context:
            self.project_context['toolbox_enabled'] = self.toolbox_enabled
        else:
            self.project_context = {'toolbox_enabled': self.toolbox_enabled}

        # Initialize core components with project context
        (
            self.conversation,
            self.cli,
            self.client,
            self.intent_classifier
        ) = self.bootstrap.initialize_components(self.config, self.project_context)

        # Update client model if changed by menu
        if provider_name and model_id:
            self.client.switch_model(model_id)
            self.cli.current_model = model_id  # Update CLI display
            self.renderer.render_info(f"✅ Modelo activo: {model_id}")

        # Setup tools only if toolbox is enabled
        if self.toolbox_enabled:
            self._setup_tools()
        else:
            self.renderer.render_info("⚡ Toolbox: OFF - Modo chat rápido")

        # Initialize handlers
        self.chat_handler = ChatHandler(self.conversation, self.renderer)
        self.response_processor = ResponseProcessor(self.conversation, self.renderer)
        self.retry_handler = RetryHandler(max_retries=2)

        # Set tool confirmation callback (called when autorun is OFF)
        self.response_processor.tool_confirm_callback = self._get_tool_confirm_callback()

        # Initialize model adapter for better tool parsing
        if self.toolbox_enabled:
            self._initialize_adapter(self.config.default_model)

        # Register commands
        self._register_commands()

        # Setup rate limiting (provider-aware)
        self.bootstrap.setup_rate_limiting(
            self.config.default_model,
            tier="free",
            provider=self.current_provider
        )

        # Setup signal handlers
        self.bootstrap.setup_signal_handlers(self._cleanup)

        # Auto-run configuration
        self.autorun_enabled = getattr(self.config, 'autorun', True)
        self.autorun_iteration = 0
        self.autorun_max_iterations = 12

        # Key listener
        self.key_listener_thread = None
        self.cancel_thinking = False
        self.thinking_active = False
        self.pending_command = None  # Command selected from menu

        self.renderer.render_info("✅ IABuilder initialized successfully")

    def _register_commands(self):
        """Register CLI commands."""
        # Provider commands
        self.cli.register_command("configure-api", configure_api_command)
        self.cli.register_command("add-provider", add_provider_command)
        self.cli.register_command("remove-api", remove_api_command)
        self.cli.register_command("status", status_command)
        self.cli.register_command("provider", provider_command)

        # Model commands
        self.cli.register_command("models", models_command)
        self.cli.register_command("model", model_command)
        self.cli.register_command("add-model", add_model_command)
        self.cli.register_command("refresh", refresh_command)
        self.cli.register_command("search-models", search_models_command)

    def _setup_tools(self):
        """Setup tools for AI use."""
        try:
            # Setup tools (project context is already in conversation system prompt)
            setup_tools(safe_mode=self.config.safe_mode)

            # Get tool count
            tools = get_tool_registry().get_schemas()
            self.renderer.render_info(f"🧰 Registered {len(tools)} tools")

        except Exception as e:
            self.error_handler.log_error(
                f"CRITICAL: Could not setup tools: {e}"
            )
            import traceback
            traceback.print_exc()
            raise  # Re-raise to make the error visible

    def _initialize_adapter(self, model_name: str):
        """Initialize or update the model adapter.

        Args:
            model_name: The model identifier
        """
        try:
            debug_separator("adapters", "INITIALIZING ADAPTER")
            debug("adapters", f"Model: {model_name}")

            adapter = get_adapter_for_model(model_name)
            self.response_processor.set_adapter(adapter)

            # Log adapter info
            info = adapter.get_model_info()
            debug_adapter(
                info.get("family", "unknown"),
                "Adapter initialized",
                f"support={info.get('support_level')}, tools={info.get('supports_tools')}"
            )
            self.renderer.render_info(f"🔌 Adapter: {info.get('family', 'generic')} ({info.get('support_level', 'unknown')})")

        except Exception as e:
            debug("adapters", f"ERROR: Could not initialize adapter: {e}")
            self.error_handler.log_warning(
                f"Could not initialize adapter: {e}. Using legacy parsing."
            )

    def _update_adapter_for_model(self, model_name: str):
        """Update adapter when model changes.

        Args:
            model_name: New model identifier
        """
        debug("adapters", f"Updating adapter for new model: {model_name}")
        self._initialize_adapter(model_name)

    def _get_tool_confirm_callback(self):
        """Create a callback for tool confirmation.

        Returns:
            Callback function that checks autorun and confirms if needed
        """
        def confirm_callback(tool_name: str, args: dict) -> bool:
            # If autorun is ON, always proceed
            if self.autorun_enabled:
                return True
            # Otherwise, ask for confirmation
            return self._confirm_tool_execution(tool_name, args)

        return confirm_callback

    def toggle_autorun(self) -> str:
        """Toggle auto-run mode on/off.

        Returns:
            Status message
        """
        self.autorun_enabled = not self.autorun_enabled
        status = "ON" if self.autorun_enabled else "OFF"
        return f"🔄 Auto-run: {status}"

    def _confirm_tool_execution(self, tool_name: str, args: dict) -> bool:
        """Ask user to confirm tool execution when auto-run is OFF.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments

        Returns:
            True if user confirms, False otherwise
        """
        import json
        args_preview = json.dumps(args, ensure_ascii=False)[:100]
        if len(json.dumps(args)) > 100:
            args_preview += "..."

        print(f"\n🔧 Ejecutar {tool_name}({args_preview})?")
        print("   [Enter] Sí  |  [n] No  |  [a] Auto-run ON")

        try:
            if platform.system() == "Windows":
                key = msvcrt.getch().decode('utf-8', errors='ignore')
            else:
                key = readchar.readkey()
            if key.lower() == 'n':
                return False
            elif key.lower() == 'a':
                self.autorun_enabled = True
                self.renderer.render_info("🔄 Auto-run: ON")
            return True
        except:
            return True

    def _check_autorun_limit(self) -> bool:
        """Check if auto-run iteration limit reached.

        Returns:
            True if should continue, False if user wants to stop
        """
        if self.autorun_iteration >= self.autorun_max_iterations:
            print(f"\n⚠️  Alcanzado límite de {self.autorun_max_iterations} iteraciones.")
            print("   [Enter] Continuar  |  [n] Detener  |  Escribe mensaje...")

            try:
                # Simple input for flexibility
                user_input = input("   > ").strip()
                if user_input.lower() == 'n':
                    return False
                elif user_input == '' or user_input.lower() in ['y', 'yes', 's', 'si']:
                    self.autorun_iteration = 0  # Reset counter
                    return True
                else:
                    # User typed something - add as new message
                    self.conversation.add_message("user", user_input)
                    self.autorun_iteration = 0
                    return True
            except:
                return False

        return True

    def start_key_listener(self):
        """Start the key listener thread.

        NOTE: Disabled because it conflicts with prompt_toolkit.
        ESC handling is now done via Ctrl+C during API calls.
        """
        # DISABLED - conflicts with prompt_toolkit terminal handling
        # self.key_listener_thread = threading.Thread(target=self._key_listener, daemon=True)
        # self.key_listener_thread.start()
        pass

    def show_commands_menu(self):
        """Show interactive menu with all available commands."""
        commands = [
            ("/help", "Mostrar ayuda completa"),
            ("/clear", "Limpiar conversación"),
            ("/compress", "Comprimir contexto"),
            ("/configure-api", "Configurar API [provider]"),
            ("/add-provider", "Agregar nuevo proveedor"),
            ("/remove-api", "Remover API [provider]"),
            ("/status", "Ver estado de proveedores"),
            ("/provider", "Cambiar proveedor activo [name]"),
            ("/models", "Listar modelos disponibles"),
            ("/model", "Cambiar modelo [name]"),
            ("/add-model", "Agregar modelo personalizado"),
            ("/refresh", "Refrescar modelos"),
            ("/search-models", "Buscar modelos [query]"),
            ("/streaming", "Activar/desactivar streaming"),
            ("/stats", "Ver estadísticas"),
            ("/resume", "Reanudar sesión [id]"),
            ("/rate", "Ver límites de rate"),
            ("/tools", "Ver herramientas disponibles"),
            ("/save", "Guardar conversación [archivo]"),
            ("/history", "Ver historial"),
            ("/autorun", "Activar/desactivar auto-run"),
            ("/toolbox", "Activar/desactivar herramientas"),
            ("/exit", "Salir del programa"),
        ]

        selected = self._interactive_command_menu(commands)
        if selected:
            # Return the selected command to be executed
            self.pending_command = selected

    def _interactive_command_menu(self, commands):
        """Show interactive command selection menu.

        Args:
            commands: List of (command, description) tuples

        Returns:
            Selected command string or None if cancelled
        """
        import sys

        current_idx = 0
        filter_text = ""
        filtered_commands = commands.copy()

        def get_filtered():
            if not filter_text:
                return commands.copy()
            return [(cmd, desc) for cmd, desc in commands if filter_text.lower() in cmd.lower()]

        def render_menu():
            # Clear screen area and render menu
            print("\033[2J\033[H", end="")  # Clear screen
            print("\n\033[1;36m📋 Comandos disponibles\033[0m")
            print(f"\033[90mFiltro: {filter_text or '(escribe para filtrar)'}\033[0m")
            print("\033[90m─" * 50 + "\033[0m")

            for i, (cmd, desc) in enumerate(filtered_commands):
                if i == current_idx:
                    # Highlighted
                    print(f"\033[1;42;30m → {cmd:20} {desc}\033[0m")
                else:
                    print(f"   \033[1;33m{cmd:20}\033[0m \033[90m{desc}\033[0m")

            print("\033[90m─" * 50 + "\033[0m")
            print("\033[90m↑↓ navegar | Enter seleccionar | Esc cancelar | letras filtrar\033[0m")

        def get_key():
            """Multi-platform key reading."""
            if platform.system() == "Windows":
                # Windows: use msvcrt for raw key input
                key = msvcrt.getch()
                if key == b'\xe0':  # Special key prefix
                    key = msvcrt.getch()
                    if key == b'H':  # Up arrow
                        return 'UP'
                    elif key == b'P':  # Down arrow
                        return 'DOWN'
                elif key == b'\r':  # Enter
                    return 'ENTER'
                elif key == b'\x1b':  # Escape
                    return 'ESC'
                elif key == b'\x08':  # Backspace
                    return 'BACKSPACE'
                else:
                    # Regular character
                    try:
                        return key.decode('utf-8', errors='ignore')
                    except:
                        return ''
            else:
                # Unix/Linux/macOS: use existing method
                key = sys.stdin.read(1)
                if key == '\x1b':  # Escape sequence
                    next1 = sys.stdin.read(1)
                    if next1 == '[':
                        next2 = sys.stdin.read(1)
                        if next2 == 'A':  # Up arrow
                            return 'UP'
                        elif next2 == 'B':  # Down arrow
                            return 'DOWN'
                    return 'ESC'  # Just ESC
                elif key == '\r' or key == '\n':  # Enter
                    return 'ENTER'
                elif key == '\x7f' or key == '\x08':  # Backspace
                    return 'BACKSPACE'
                elif key == '\x03':  # Ctrl+C
                    return 'CTRL_C'
                return key

        try:
            if platform.system() != "Windows":
                # Unix setup
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setraw(fd)

            render_menu()

            while True:
                key = get_key()

                if key == 'ESC':  # Cancel
                    return None
                elif key == 'ENTER':  # Select
                    if filtered_commands:
                        return filtered_commands[current_idx][0]
                    return None
                elif key == 'UP':  # Navigate up
                    current_idx = max(0, current_idx - 1)
                elif key == 'DOWN':  # Navigate down
                    current_idx = min(len(filtered_commands) - 1, current_idx + 1)
                elif key == 'BACKSPACE':  # Remove filter character
                    filter_text = filter_text[:-1]
                    filtered_commands = get_filtered()
                    current_idx = 0
                elif key == 'CTRL_C':  # Cancel
                    return None
                elif key and (key.isalnum() or key in '-_'):  # Add to filter
                    filter_text += key
                    filtered_commands = get_filtered()
                    current_idx = 0

                if filtered_commands:
                    current_idx = min(current_idx, len(filtered_commands) - 1)

                render_menu()

        except Exception as e:
            return None
        finally:
            if platform.system() != "Windows":
                # Unix cleanup
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            print("\033[2J\033[H", end="")  # Clear screen after menu

    def run(self):
        """Run the main application loop."""
        self.renderer.render_info(
            "\n💡 Type /help for commands or just start chatting!\n"
        )

        # Setup key listener for ESC and /
        self.start_key_listener()

        while self.cli.running:
            try:
                # Check for pending command from menu
                if self.pending_command:
                    user_input = self.pending_command
                    self.pending_command = None
                    print(f"\n\033[1;36m> {user_input}\033[0m")  # Show selected command
                else:
                    # Get user input
                    user_input = self.cli.get_input()

                    if user_input is None:
                        break

                    user_input = user_input.strip()
                    if not user_input:
                        continue

                # Handle exit commands
                if user_input.lower() in ["exit", "quit", "/exit", "/quit"]:
                    break

                # Handle commands
                if self.cli.is_command(user_input):
                    command, args = self.cli.parse_command(user_input)
                    response = self.cli.handle_command(command, args)

                    if response and isinstance(response, str):
                        print("\n" + response + "\n")

                    # Update client model if changed
                    if command == "model" and isinstance(response, str) and "switched" in response.lower():
                        # Extract the new model ID from the response message
                        # Format: "Switched to model: deepseek/deepseek-r1"
                        if "Switched to model:" in response:
                            new_model_id = response.split("Switched to model:")[-1].strip()
                            # Update CLI display model
                            self.cli.current_model = new_model_id
                            # Update client
                            self.client.switch_model(new_model_id)
                            # Also update the adapter for the new model
                            if self.toolbox_enabled:
                                self._update_adapter_for_model(new_model_id)

                    # Handle provider switch - reinitialize client
                    if command == "provider" and "Proveedor" in str(response):
                        self._update_client_for_provider()

                    # Sync autorun state (reload from config file)
                    if command == "autorun":
                        from .config.config import get_config_manager
                        self.config = get_config_manager().load()
                        self.autorun_enabled = getattr(self.config, 'autorun', True)

                    continue

                # Handle chat messages
                self._handle_chat_message(user_input)

            except KeyboardInterrupt:
                print("\n\nUse /exit to quit.\n")
                continue
            except EOFError:
                print("\n")
                break
            except Exception as e:
                self.error_handler.handle_error(
                    e,
                    context={"phase": "main_loop"}
                )
                print(f"\n❌ Error: {e}\n")

        self._cleanup()

    def _handle_chat_message(self, message: str, skip_menu: bool = False):
        """Handle a chat message with streaming and auto-run support.

        Flow:
        1. Stream thinking/response (visible to user)
        2. If tool calls: confirm (if autorun OFF) -> execute -> loop
        3. Final response without stream

        Args:
            message: User message
            skip_menu: Unused (kept for compatibility)
        """
        import re
        import sys
        import time

        # Let chat handler process special cases (only greetings)
        if self.chat_handler.handle_message(message):
            return

        # Reset iteration counter for new user message
        self.autorun_iteration = 0

        # Only include tools if toolbox is enabled
        tools = get_tool_registry().get_schemas() if self.toolbox_enabled else None
        use_streaming = getattr(self.config, 'streaming', True)

        # Pattern for thinking tags
        think_pattern = re.compile(r'<think>.*?</think>', re.DOTALL | re.IGNORECASE)

        try:
            while True:
                # Check autorun limit
                if not self._check_autorun_limit():
                    self.renderer.render_info("⏹️  Auto-run detenido.")
                    break

                self.autorun_iteration += 1

                # Streaming callback for thinking visibility
                streamed_content = []
                in_thinking = False
                thinking_lines = 0

                def streaming_callback(chunk: str):
                    nonlocal in_thinking, thinking_lines
                    streamed_content.append(chunk)

                    # Detect thinking start
                    if '<think>' in chunk.lower():
                        in_thinking = True
                        sys.stdout.write('\033[90m')  # Gray
                        sys.stdout.flush()

                    # Print chunk
                    if in_thinking:
                        thinking_lines += chunk.count('\n')
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                    else:
                        print(chunk, end='', flush=True)

                    # Detect thinking end
                    if '</think>' in chunk.lower():
                        in_thinking = False
                        sys.stdout.write('\033[0m')  # Reset
                        sys.stdout.flush()
                        time.sleep(1)  # Show thinking for 1 second
                        # Clear thinking lines
                        for _ in range(thinking_lines + 1):
                            sys.stdout.write('\033[A\033[K')
                        sys.stdout.flush()
                        thinking_lines = 0

                if use_streaming:
                    print("\n🤖 ", end='', flush=True)

                # Determine if we should use native tool message format
                # (adapter says it supports it = don't convert to text)
                use_native_tools = (
                    hasattr(self.response_processor, 'adapter') and
                    self.response_processor.adapter and
                    getattr(self.response_processor.adapter, 'supports_native_tool_messages', False)
                )
                convert_to_user = not use_native_tools
                debug("context", f"Tool message format: {'NATIVE' if use_native_tools else 'TEXT'}")

                # Call LLM with streaming
                response = self.retry_handler.call_with_retry(
                    self.client.send_message,
                    messages=self.conversation.get_messages_for_api(convert_tool_to_user=convert_to_user),
                    tools=tools,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    stream=use_streaming,
                    callback=streaming_callback if use_streaming else None
                )

                if use_streaming and streamed_content:
                    print()  # Newline after streaming

                # Process response for tool calls
                result = self.response_processor.process_response(response, tools)

                # If tools need execution
                if result == ResponseProcessor.NEEDS_FOLLOWUP:
                    # Show iteration counter
                    print(f"\033[90m[Iteración {self.autorun_iteration}/{self.autorun_max_iterations}]\033[0m")
                    continue  # Loop back to get model's next response

                # No more tool calls - final response
                if use_streaming and streamed_content:
                    # Content was streamed, clean and save
                    full_text = ''.join(streamed_content)
                    full_text = think_pattern.sub('', full_text).strip()
                    if full_text:
                        self.conversation.add_message("assistant", full_text)
                elif result and result.strip():
                    self.renderer.render_assistant_message(result)

                break  # Exit loop

            # Check context warning
            self._check_context_warning()

        except ToolCallError as e:
            if e.failed_generation:
                self.renderer.render_info("🔄 Processing tool call...")
                malformed_calls = self.response_processor._parse_malformed_tool_calls(
                    e.failed_generation
                )
                if malformed_calls:
                    result = self.response_processor._process_malformed_tools(
                        malformed_calls, ""
                    )
                    if result == ResponseProcessor.NEEDS_FOLLOWUP:
                        # Continue with auto-run loop
                        self._handle_chat_message("", skip_menu=True)
            else:
                self.renderer.render_error(str(e))

        except KeyboardInterrupt:
            print("\n⏸️  Interrumpido")

        except Exception as e:
            error_msg = self.error_handler.handle_api_error(
                "AI", e, request_data={"message": message[:100]}
            )
            print(f"\n{error_msg}\n")

    def _check_context_warning(self):
        """Check context usage and show warning if approaching limit."""
        try:
            # Get model's context window (default 128K for most modern models)
            context_window = 128000

            # Try to get actual context window from model capabilities
            try:
                from .config.model_capabilities import get_model_capability
                cap = get_model_capability(self.cli.current_model)
                if cap and cap.context_window > 0:
                    context_window = cap.context_window
            except Exception:
                pass

            status = self.conversation.get_context_status(context_window)

            # Show warning if needed
            if status["warning"]:
                print()  # Empty line before warning
                if status["level"] == "critical":
                    self.renderer.render_error(status["warning"])
                else:
                    self.renderer.render_warning(status["warning"])

        except Exception as e:
            self.error_handler.log_debug(f"Context check failed: {e}")

    def _update_client_for_provider(self):
        """Update the AI client when provider changes.

        Reinitializes the client with the new active provider's configuration.
        """
        try:
            from .config.provider_config import get_multi_provider_config_manager

            provider_config = get_multi_provider_config_manager()
            active_provider = provider_config.get_active_provider()

            if not active_provider:
                self.renderer.render_warning("⚠️ No hay proveedor activo")
                return

            api_key = provider_config.get_provider_api_key(active_provider.name)
            model = active_provider.default_model or self.config.default_model

            if active_provider.name == "openrouter":
                # OpenRouter uses OpenAI-compatible API - use wrapper
                from .client_openai import OpenAICompatibleClient
                self.client = OpenAICompatibleClient(
                    api_key=api_key,
                    model=model,
                    base_url="https://openrouter.ai/api/v1"
                )
                self.renderer.render_info(f"🔄 Cliente actualizado: OpenRouter")
            elif active_provider.name == "groq":
                # Use native Groq client
                self.client = GroqClient(api_key=api_key, model=model)
                self.renderer.render_info(f"🔄 Cliente actualizado: Groq")
            elif active_provider.name == "google":
                # Google Gemini uses OpenAI-compatible API at v1beta/openai endpoint
                from .client_openai import OpenAICompatibleClient
                self.client = OpenAICompatibleClient(
                    api_key=api_key,
                    model=model,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                self.renderer.render_info(f"🔄 Cliente actualizado: Google Gemini")
            else:
                # Other providers - try OpenAI-compatible mode
                base_url = active_provider.base_url
                if base_url:
                    from .client_openai import OpenAICompatibleClient
                    self.client = OpenAICompatibleClient(
                        api_key=api_key,
                        model=model,
                        base_url=base_url
                    )
                    self.renderer.render_info(f"🔄 Cliente actualizado: {active_provider.name}")
                else:
                    self.renderer.render_warning(
                        f"⚠️ Proveedor {active_provider.name} no tiene base_url configurada"
                    )
                    return

            # Update CLI display
            self.cli.current_model = model

            self.renderer.render_info(f"✅ Modelo activo: {model}")

        except ImportError as e:
            self.renderer.render_warning(
                f"⚠️ Error de importación: {e}. Instala 'openai' con: pip install openai"
            )
        except Exception as e:
            self.error_handler.log_warning(f"Error updating client: {e}")
            self.renderer.render_error(f"Error actualizando cliente: {e}")

    def _cleanup(self):
        """Cleanup resources."""
        try:
            # Save conversation
            if self.config.auto_save:
                self.conversation.save()

            # Stop background processes
            from .tools.process_manager import get_process_manager
            get_process_manager().cleanup()

            self.renderer.render_info("\n👋 Session ended. Goodbye!\n")

        except Exception as e:
            self.error_handler.log_warning(f"Cleanup error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="IABuilder - Intelligent AI Code Assistant"
    )
    parser.add_argument(
        "--dir",
        help="Working directory (defaults to current directory)",
        default=None
    )

    args = parser.parse_args()

    try:
        app = IABuilderApp(working_directory=args.dir)
        return app.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
