"""Interactive CLI interface using prompt-toolkit."""

import re
from pathlib import Path
from typing import Callable, List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import confirm
from prompt_toolkit.styles import Style

from .config import get_config_manager
from .renderer import Renderer


def get_rate_limiter_status():
    """Get rate limiter status for display."""
    try:
        from .rate_limiter import get_rate_limiter
        status = get_rate_limiter().get_current_usage()

        return f"""# Rate Limiting Status

## Current Usage
- **Tokens this minute:** {status['tokens_this_minute']:,} / {status['effective_limit']:,}
- **Usage percentage:** {status['usage_percentage']:.1f}%
- **Can make request:** {'✅ Yes' if status['can_make_request'] else '❌ No'}

## Limits
- **TPM Limit:** {status['tpm_limit']:,} tokens/minute
- **Effective limit:** {status['effective_limit']:,} tokens/minute (with buffer)
- **Buffer:** {status['tpm_limit'] - status['effective_limit']:,} tokens

## History
- **Usage entries tracked:** {status['entries_count']}

**Note:** If usage approaches limit, the system will automatically wait 60 seconds."""
    except Exception as e:
        return f"❌ Error getting rate limiter status: {e}"


class CommandCompleter(Completer):
    """Auto-completion for commands and paths."""

    def __init__(self, commands: List[str]):
        """Initialize completer.

        Args:
            commands: List of available commands
        """
        self.commands = commands
        self.file_completer = PathCompleter()

    def get_completions(self, document, complete_event):
        """Get completions for current input."""
        text = document.text_before_cursor

        # If starts with slash, complete commands
        if text.startswith("/"):
            for cmd in self.commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))

        # If looks like a file path (contains / or .), complete paths
        elif (
            "/" in text
            or "." in text
            or text.startswith("./")
            or text.startswith("../")
        ):
            yield from self.file_completer.get_completions(document, complete_event)

        # Otherwise, no completion
        else:
            pass


class PathCompleter(Completer):
    """File path completer."""

    def get_completions(self, document, complete_event):
        """Complete file paths."""
        text = document.text_before_cursor

        try:
            # Get the directory and partial filename
            if "/" in text:
                dir_path = Path(text).parent
                partial = Path(text).name
            else:
                dir_path = Path(".")
                partial = text

            # List files in directory
            if dir_path.exists():
                for item in dir_path.iterdir():
                    if item.name.startswith(partial):
                        # Add trailing slash for directories
                        suffix = "/" if item.is_dir() else ""
                        yield Completion(
                            item.name + suffix,
                            start_position=-len(partial),
                            display=item.name + suffix,
                        )
        except Exception:
            pass


class CLI:
    """Interactive CLI interface for IABuilder."""

    def __init__(self, conversation=None):
        """Initialize CLI."""
        self.renderer = Renderer()
        self.config_manager = get_config_manager()

        # Load config
        self.config = self.config_manager.load()

        # Store for dynamically registered commands
        self.registered_commands = {}

        # Setup prompt session
        history_file = self.config_manager.config_dir / "history.txt"
        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            completer=self._setup_completer(),
            style=self._setup_style(),
            key_bindings=self._setup_key_bindings(),
            complete_while_typing=True,  # Show completions as you type
            multiline=True,  # Enable multi-line editing
            prompt_continuation=self._get_continuation_prompt,  # Show continuation marker
        )

        # State
        self.current_model = self.config.default_model
        self.running = True
        self.conversation = conversation

    def _setup_completer(self) -> CommandCompleter:
        """Setup command completer."""
        commands = [
            # Basic commands
            "/help",
            "/clear",
            "/history",
            "/save",
            "/tools",
            "/compress",
            "/stats",
            "/rate",
            "/resume",
            "/load",
            "/streaming",
            "/toolbox",
            "/debug",
            "/autorun",
            "/exit",
            "/quit",
            # Provider management
            "/provider",
            "/configure-api",
            "/add-provider",
            "/remove-api",
            "/status",
            # Model management
            "/model",
            "/models",
            "/add-model",
            "/refresh",
            "/search-models",
        ]
        return CommandCompleter(commands)

    def _setup_style(self) -> Style:
        """Setup prompt style."""
        return Style.from_dict(
            {
                "prompt": "bold cyan",
                "model": "bold green",
                "tools": "bold yellow",
            }
        )

    def _get_continuation_prompt(self, width, line_number, is_soft_wrap):
        """Return continuation prompt for multi-line input."""
        return "    "  # Just indentation, no dots

    def _setup_key_bindings(self) -> KeyBindings:
        """Setup custom key bindings."""
        from prompt_toolkit.filters import has_focus
        from prompt_toolkit.key_binding.bindings.named_commands import accept_line

        kb = KeyBindings()

        @kb.add("c-c")
        def handle_ctrl_c(event):
            """Handle Ctrl+C to cancel current input."""
            event.app.current_buffer.reset()
            self.renderer.render_info("Input cancelled. Use /exit to quit.")

        @kb.add("escape", "enter")
        def handle_escape_enter(event):
            """Escape+Enter: Add new line for multi-line input."""
            event.current_buffer.insert_text("\n")

        @kb.add("enter")
        def handle_enter(event):
            """Enter: Always submit the input."""
            event.current_buffer.validate_and_handle()

        return kb

    def get_prompt(self) -> str:
        """Get the current prompt string."""
        model_short = self._shorten_model_name(self.current_model)

        # Indicar que herramientas están disponibles
        return [
            ("class:prompt", "iabuilder"),
            ("class:model", f" [{model_short}]"),
            ("class:tools", " [🧰]"),  # Indicador de herramientas disponibles
            ("class:prompt", " > "),
        ]

    def _shorten_model_name(self, model: str) -> str:
        """Shorten model name for display in prompt.

        Args:
            model: Full model name

        Returns:
            Shortened model name
        """
        if not model:
            return "no-model"

        # Handle OpenRouter format: provider/model-name:variant
        if "/" in model:
            # Extract just the model name part
            parts = model.split("/")
            model_part = parts[-1]  # Get the model name after provider

            # Remove :free or :variant suffix for display
            if ":" in model_part:
                model_part = model_part.split(":")[0]

            # Shorten common model names
            model_part = model_part.replace("-instruct", "")
            model_part = model_part.replace("-chat", "")

            # Keep it reasonably short (max 25 chars)
            if len(model_part) > 25:
                model_part = model_part[:22] + "..."

            return model_part

        # Handle Groq format
        model = model.replace("llama-3.3-70b-versatile", "llama-3.3-70b")
        model = model.replace("llama-3.1-8b-instant", "llama-3.1-8b")
        model = model.replace("-instruct", "")

        return model

    def is_command(self, text: str) -> bool:
        """Check if input is a command."""
        return text.strip().startswith("/")

    def register_command(self, name: str, handler: Callable):
        """Register a custom command handler.

        Args:
            name: Command name (without leading slash)
            handler: Function to call with args when command is invoked
        """
        self.registered_commands[name.lower()] = handler

    def parse_command(self, text: str) -> tuple[str, List[str]]:
        """Parse slash command into command and args."""
        text = text.strip()
        if not text.startswith("/"):
            return "", []

        parts = text[1:].split()
        if not parts:
            return "", []

        command = parts[0]
        args = parts[1:]
        return command, args

    def handle_command(self, command: str, args: List[str]) -> Optional[str]:
        """Handle a slash command.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            Response message or None if command was handled internally
        """
        command = command.lower()

        if command == "help":
            return self._cmd_help()
        elif command == "clear":
            return self._cmd_clear()
        elif command == "history":
            return self._cmd_history(args)
        elif command == "save":
            return self._cmd_save(args)
        elif command == "tools":
            return self._cmd_tools()
        elif command == "compress":
            return self._cmd_compress()
        elif command == "stats":
            return self._cmd_stats()
        elif command == "resume":
            return self._cmd_resume(args)
        elif command == "load":
            return self._cmd_load(args)
        elif command == "streaming":
            return self._cmd_streaming()
        elif command == "autorun":
            return self._cmd_autorun()
        elif command == "toolbox":
            return self._cmd_toolbox()
        elif command == "debug":
            return self._cmd_debug(args)
        elif command == "rate":
            return self._cmd_rate()
        elif command in ["exit", "quit"]:
            self.running = False
            return "Goodbye! 👋"
        else:
            # Check for dynamically registered commands
            if command in self.registered_commands:
                try:
                    # Call the registered handler with args
                    # Most commands expect Optional[str] parameters, so pass first arg or None
                    handler = self.registered_commands[command]
                    if args:
                        result = handler(args[0] if len(args) > 0 else None)
                    else:
                        result = handler()

                    # Return string result or None if handler handled it internally
                    return result if isinstance(result, str) else None
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    return f"Error executing command /{command}: {e}"

            return f"Unknown command: /{command}. Type /help for available commands."

    def _cmd_help(self) -> str:
        """Show help text."""
        help_text = """
# IABuilder Help

## Chat
Just type your message to chat with the AI. It has access to programming tools.

## Basic Commands
- `/help` - Show this help
- `/clear` - Clear conversation history
- `/history` - Show conversation history
- `/save [filename]` - Export conversation to markdown (for reading)
- `/load [session]` - List or load saved sessions from history
- `/tools` - List available tools
- `/compress` - Manually trigger context compression
- `/stats` - Show compression and conversation statistics
- `/rate` - Show rate limiting status and token usage
- `/resume [session_id]` - View compressed session details
- `/streaming` - Toggle streaming mode (see text as it's generated)
- `/toolbox` - Toggle tools/function calling on/off
- `/autorun` - Toggle auto-run mode (execute tools without confirmation)
- `/debug [on|off|status|category]` - Toggle debug output
- `/exit` or `/quit` - Exit the application

## Provider Management (Multi-Provider Support)
- `/provider [name]` - Switch active API provider and select model
- `/configure-api [provider]` - Configure API for preset providers (groq, openai, anthropic, google, openrouter)
- `/add-provider` - Add custom LLM provider
- `/remove-api [name]` - Remove a configured provider
- `/status` - Show all configured providers and their status

## Model Management
- `/models [provider]` - List available models (all or from specific provider)
- `/model [name]` - Switch to a different model
- `/add-model` - Manually add a model to registry
- `/refresh [provider]` - Refresh model list from APIs
- `/search-models [query]` - Search for models by name or description

## Tools Available
The AI can use these tools automatically:
- **read_file** - Read file contents
- **write_file** - Write to files
- **edit_file** - Edit existing files
- **execute_bash** - Run any shell command (grep, find, npm, pip, docker, git, etc.)
- **web_search** - Search the internet with DuckDuckGo

## Tips
- Enter: envía el mensaje
- Escape+Enter: añade nueva línea (para mensajes multi-línea)
- Ctrl+C: cancela el input actual
- Tab: autocompletado de comandos y rutas
- ↑↓: navegar historial de comandos
        """
        return help_text.strip()

    def _cmd_clear(self) -> str:
        """Handle clear command."""
        if confirm("Clear conversation history? This cannot be undone."):
            if self.conversation:
                self.conversation.clear()
            return "Conversation cleared."
        else:
            return "Clear cancelled."

    def _cmd_history(self, args: List[str]) -> str:
        """Handle history command."""
        if not self.conversation:
            return "Conversation not available."

        messages = self.conversation.get_messages()
        if not messages:
            return "No conversation history."

        response = "# Conversation History\n\n"
        for i, msg in enumerate(messages[-20:], 1):  # Show last 20 messages
            role = msg.get("role", "unknown").upper()
            timestamp = msg.get("timestamp", "")[:19]  # YYYY-MM-DDTHH:MM:SS
            content = msg.get("content", "")

            response += f"## {i}. {role} ({timestamp})\n"

            if content:
                # Truncate long content
                if len(content) > 200:
                    content = content[:200] + "..."
                response += f"{content}\n\n"

            # Show tool calls
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    func_name = "unknown"
                    if isinstance(tc, str):
                        func_name = tc
                    elif isinstance(tc, dict):
                        func_name = tc.get("function", {}).get("name", "unknown")
                    elif hasattr(tc, 'function'):
                        func_name = getattr(getattr(tc, 'function', None), 'name', 'unknown')
                    response += f"**Called:** `{func_name}`\n\n"

        response += f"**Total messages:** {len(messages)}"
        return response

    def _cmd_save(self, args: List[str]) -> str:
        """Handle save command."""
        if not self.conversation:
            return "Conversation not available."

        filename = (
            args[0] if args else f"conversation_{self.conversation.session_id[:8]}.md"
        )

        # Add .md extension if not present
        if not filename.endswith(".md"):
            filename += ".md"

        try:
            export_path = Path(filename)
            self.conversation.export_markdown(export_path)
            return f"Conversation exported to: {export_path.absolute()}"
        except Exception as e:
            return f"Failed to export conversation: {e}"

    def _cmd_tools(self) -> str:
        """Handle tools command."""
        try:
            from .tools import get_tool_registry

            registry = get_tool_registry()
            tool_names = registry.list_tools()

            if not tool_names:
                return "No tools registered."

            response = "# Available Tools\n\n"
            for name in sorted(tool_names):
                tool = registry.get(name)
                if tool:
                    response += f"## `{name}`\n"
                    response += f"{tool.description}\n\n"

            return response
        except Exception as e:
            return f"Error loading tools: {e}"

    def _cmd_compress(self) -> str:
        """Handle compress command."""
        if not self.conversation:
            return "No active conversation."

        try:
            from .context_compressor import ContextCompressor

            compressor = ContextCompressor()

            if compressor.should_compress(self.conversation):
                result = compressor.compress_conversation(self.conversation)
                return f"✅ Context compressed!\n• Reduced from {result['original_tokens']} tokens\n• {result['compressed_messages']} messages remaining\n• Compressed version saved"
            else:
                current_tokens = compressor.estimate_conversation_tokens(
                    self.conversation.messages
                )
                return f"ℹ️  Compression not needed yet.\n• Current tokens: {current_tokens}\n• Threshold: {compressor.compression_threshold}"

        except Exception as e:
            return f"❌ Compression failed: {e}"

    def _cmd_stats(self) -> str:
        """Handle stats command."""
        if not self.conversation:
            return "No active conversation."

        try:
            stats = self.conversation.get_compression_stats()

            response = "# Conversation Statistics\n\n"

            if stats.get("compression_enabled"):
                response += f"## Compression Status\n"
                response += f"- **Enabled:** ✅ Yes\n"
                response += (
                    f"- **Compressions performed:** {stats['compression_count']}\n"
                )
                response += f"- **Current tokens:** {stats['current_tokens']:,}\n"
                response += f"- **Max tokens:** {stats['max_tokens']:,}\n"
                response += f"- **Threshold:** {stats['compression_threshold']:,}\n"
                response += f"- **Should compress:** {'✅ Yes' if stats['should_compress'] else '❌ No'}\n"
                response += (
                    f"- **Compression ratio:** {stats['compression_ratio']:.2f}x\n\n"
                )
            else:
                response += "❌ **Compression disabled**\n\n"

            # Message stats
            response += f"## Message Statistics\n"
            response += f"- **Total messages:** {len(self.conversation.messages)}\n"
            response += f"- **Session ID:** `{self.conversation.session_id}`\n"

            # Tool usage in current session
            tool_calls = sum(
                1 for msg in self.conversation.messages if msg.get("tool_calls")
            )
            response += f"- **Tool calls in session:** {tool_calls}\n"

            return response

        except Exception as e:
            return f"❌ Error getting stats: {e}"

    def _cmd_rate(self) -> str:
        """Handle rate command - show rate limiting status."""
        return get_rate_limiter_status()

    def _cmd_streaming(self) -> str:
        """Toggle streaming mode on/off."""
        try:
            from .config.config import get_config_manager

            config_manager = get_config_manager()
            config = config_manager.load()

            # Toggle streaming
            current = getattr(config, 'streaming', True)
            new_value = not current
            config.streaming = new_value
            config_manager.save(config)

            status = "✅ ACTIVADO" if new_value else "❌ DESACTIVADO"
            return f"🎬 Streaming {status}\n\nCon streaming verás las respuestas letra por letra."

        except Exception as e:
            return f"❌ Error toggling streaming: {e}"

    def _cmd_autorun(self) -> str:
        """Toggle auto-run mode on/off."""
        try:
            from .config.config import get_config_manager

            config_manager = get_config_manager()
            config = config_manager.load()

            # Toggle autorun
            current = getattr(config, 'autorun', True)
            new_value = not current
            config.autorun = new_value
            config_manager.save(config)

            if new_value:
                status = "✅ ON"
                desc = "Las herramientas se ejecutarán automáticamente (máx 12 iteraciones)."
            else:
                status = "❌ OFF"
                desc = "Se pedirá confirmación antes de ejecutar cada herramienta."

            return f"🔄 Auto-run: {status}\n\n{desc}"

        except Exception as e:
            return f"❌ Error toggling autorun: {e}"

    def _cmd_toolbox(self) -> str:
        """Toggle toolbox (tools/function calling) on/off."""
        try:
            from .config.config import get_config_manager

            config_manager = get_config_manager()
            config = config_manager.load()

            # Toggle toolbox
            current = getattr(config, 'toolbox', True)
            new_value = not current
            config.toolbox = new_value
            config_manager.save(config)

            if new_value:
                status = "🧰 ON"
                desc = "Herramientas habilitadas (execute_bash, read_file, write_file, etc.)\n⚠️  Reinicia IABuilder para aplicar el cambio."
            else:
                status = "⚡ OFF"
                desc = "Modo chat rápido - sin herramientas.\n⚠️  Reinicia IABuilder para aplicar el cambio."

            return f"🔧 Toolbox: {status}\n\n{desc}"

        except Exception as e:
            return f"❌ Error toggling toolbox: {e}"

    def _cmd_debug(self, args: List[str]) -> str:
        """Toggle debug output on/off or configure categories.

        Usage:
            /debug          - Toggle all debug on/off
            /debug on       - Enable all debug
            /debug off      - Disable all debug
            /debug status   - Show current debug status
            /debug <cat>    - Toggle specific category (chat, tools, streaming, adapters, api, context)
        """
        try:
            from .debug import DEBUG_ENABLED, DEBUG_FLAGS, set_debug, set_debug_category, get_debug_status

            if not args:
                # Toggle all debug
                import iabuilder.debug as dbg
                dbg.DEBUG_ENABLED = not dbg.DEBUG_ENABLED
                status = "🔍 ON" if dbg.DEBUG_ENABLED else "🔇 OFF"
                return f"Debug: {status}"

            arg = args[0].lower()

            if arg == "on":
                import iabuilder.debug as dbg
                dbg.DEBUG_ENABLED = True
                return "🔍 Debug: ON (all categories)"

            elif arg == "off":
                import iabuilder.debug as dbg
                dbg.DEBUG_ENABLED = False
                return "🔇 Debug: OFF"

            elif arg == "status":
                status = get_debug_status()
                lines = [
                    f"Debug master switch: {'ON' if status['enabled'] else 'OFF'}",
                    "",
                    "Categories:"
                ]
                for cat, enabled in status['categories'].items():
                    icon = "✅" if enabled else "❌"
                    lines.append(f"  {icon} {cat}")
                return "\n".join(lines)

            elif arg in DEBUG_FLAGS:
                # Toggle specific category
                import iabuilder.debug as dbg
                dbg.DEBUG_FLAGS[arg] = not dbg.DEBUG_FLAGS[arg]
                status = "ON" if dbg.DEBUG_FLAGS[arg] else "OFF"
                return f"Debug category '{arg}': {status}"

            else:
                categories = ", ".join(DEBUG_FLAGS.keys())
                return f"❌ Unknown arg: {arg}\nValid: on, off, status, {categories}"

        except Exception as e:
            return f"❌ Error: {e}"

    def _cmd_resume(self, args: List[str]) -> str:
        """Handle resume command."""
        if not self.conversation:
            return "No active conversation."

        try:
            if args and args[0]:
                # Load specific compressed session
                session_id = args[0]
                compressed_data = self.conversation.load_compressed_session(session_id)

                if compressed_data:
                    response = f"# Compressed Session: {session_id}\n\n"
                    response += f"**Compressed at:** {compressed_data.get('compressed_at', 'Unknown')}\n\n"
                    response += f"**Original stats:** {compressed_data['original_stats']['total_messages']} messages, {compressed_data['original_stats']['total_tokens']:,} tokens\n\n"
                    response += f"**Tools used:** {', '.join(compressed_data['tool_usage']['tools_used'])}\n\n"
                    response += f"**Key files:** {', '.join(compressed_data.get('key_files', [])[:5])}\n\n"
                    response += f"**Summary:** {compressed_data.get('summary_text', 'No summary available')}\n"

                    return response
                else:
                    return f"❌ Compressed session '{session_id}' not found."
            else:
                # List all compressed sessions
                compressed_sessions = self.conversation.list_compressed_sessions()

                if not compressed_sessions:
                    return "ℹ️  No compressed conversations found."

                response = "# Compressed Conversations\n\n"
                for session in compressed_sessions[:10]:  # Show last 10
                    session_id = session.get("session_id", "Unknown")
                    compressed_at = session.get("compressed_at", "Unknown")[
                        :19
                    ]  # YYYY-MM-DDTHH:MM:SS
                    orig_tokens = session.get("original_stats", {}).get(
                        "total_tokens", 0
                    )
                    tools_used = len(
                        session.get("tool_usage", {}).get("tools_used", [])
                    )

                    response += f"## `{session_id}`\n"
                    response += f"Compressed: {compressed_at}\n"
                    response += f"Original tokens: {orig_tokens:,}\n"
                    response += f"Tools used: {tools_used}\n\n"

                response += (
                    f"**Total compressed sessions:** {len(compressed_sessions)}\n"
                )
                response += "*Use `/resume <session_id>` to view details of a specific session.*"

                return response

        except Exception as e:
            return f"❌ Error accessing compressed sessions: {e}"

    def _cmd_load(self, args: List[str]) -> str:
        """Handle load command - interactive session selector."""
        try:
            import json

            history_dir = self.config_manager.config_dir / "history"

            if not history_dir.exists():
                return "ℹ️  No hay directorio de historial."

            session_files = sorted(history_dir.glob("session_*.json"), reverse=True)

            if not session_files:
                return "ℹ️  No hay sesiones guardadas."

            if args and args[0]:
                # Load specific session by name
                return self._load_session_by_name(args[0], session_files)
            else:
                # Show interactive menu
                return self._show_session_menu(session_files)

        except Exception as e:
            return f"❌ Error: {e}"

    def _load_session_by_name(self, session_id: str, session_files: list) -> str:
        """Load a session by name."""
        import json

        matching_files = [f for f in session_files if session_id in f.name]

        if not matching_files:
            return f"❌ Sesión '{session_id}' no encontrada."

        session_file = matching_files[0]

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            if self.conversation:
                messages = session_data.get('messages', [])
                if messages:
                    self.conversation.messages = messages
                    self.conversation.session_id = session_data.get('session_id', self.conversation.session_id)

                    msg_count = len(messages)
                    return f"✅ Sesión cargada: {session_file.name}\n• {msg_count} mensajes restaurados\n• Session ID: {self.conversation.session_id[:8]}..."
                else:
                    return "⚠️  La sesión no tiene mensajes."
            else:
                return "❌ No hay conversación activa para cargar."

        except json.JSONDecodeError:
            return f"❌ Error: El archivo de sesión está corrupto."

    def _show_session_menu(self, session_files: list) -> str:
        """Show interactive menu to select a session."""
        import json
        from prompt_toolkit.shortcuts import radiolist_dialog
        from prompt_toolkit.styles import Style as PTStyle

        # Build choices list
        choices = []
        for session_file in session_files[:20]:  # Limit to 20 most recent
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                msg_count = len(data.get('messages', []))
                created = session_file.name.replace('session_', '').replace('.json', '')

                # Format date: 20251228_163943 -> 2025-12-28 16:39
                if len(created) >= 15:
                    date_str = f"{created[:4]}-{created[4:6]}-{created[6:8]} {created[9:11]}:{created[11:13]}"
                else:
                    date_str = created

                # Get first user message as preview
                preview = ""
                for msg in data.get('messages', []):
                    if msg.get('role') == 'user':
                        content = msg.get('content', '')[:40]
                        if content:
                            preview = f" - \"{content}...\""
                        break

                label = f"📅 {date_str} | 💬 {msg_count} msgs{preview}"
                choices.append((session_file.stem, label))

            except Exception:
                choices.append((session_file.stem, f"📅 {session_file.stem} (error)"))

        if not choices:
            return "ℹ️  No hay sesiones válidas."

        # Custom style for the dialog
        dialog_style = PTStyle.from_dict({
            'dialog': 'bg:#1a1a2e',
            'dialog.body': 'bg:#16213e',
            'dialog frame.label': 'bg:#0f3460 #ffffff',
            'dialog.body label': '#e94560',
            'button': 'bg:#0f3460',
            'button.focused': 'bg:#e94560',
            'radiolist': 'bg:#16213e #ffffff',
        })

        # Show dialog
        result = radiolist_dialog(
            title="📂 Cargar Sesión",
            text="Usa ↑↓ para navegar, Enter para seleccionar, Esc para cancelar:",
            values=choices,
            style=dialog_style,
        ).run()

        if result:
            # Load the selected session
            return self._load_session_by_name(result, session_files)
        else:
            return "ℹ️  Selección cancelada."

    def get_input(self) -> Optional[str]:
        """Get user input from prompt with autocompletion.

        Returns:
            User input or None if EOF
        """
        try:
            # Get context status bar
            context_info = self._get_context_bar()

            # Show status bar above prompt
            if context_info:
                print(context_info)

            # Use prompt_toolkit session for autocompletion
            user_input = self.session.prompt(self.get_prompt())
            return user_input

        except KeyboardInterrupt:
            print()  # New line
            return None
        except EOFError:
            self.running = False
            return None

    def _get_context_bar(self) -> str:
        """Get context status bar string.

        Returns:
            Formatted status bar or empty string
        """
        try:
            if not self.conversation:
                return ""

            # Get token estimate
            tokens = self.conversation.get_token_estimate()

            # Estimate context window (default 128K)
            max_context = 128000
            try:
                from .config.model_capabilities import get_model_capability
                cap = get_model_capability(self.current_model)
                if cap and cap.context_window > 0:
                    max_context = cap.context_window
            except Exception:
                pass

            percentage = (tokens / max_context) * 100 if max_context > 0 else 0

            # Format tokens for display
            if tokens >= 1000:
                tokens_display = f"{tokens / 1000:.1f}K"
            else:
                tokens_display = str(tokens)

            # Create progress bar
            bar_width = 20
            filled = int(bar_width * percentage / 100)
            bar = "█" * filled + "░" * (bar_width - filled)

            # Color based on usage
            if percentage >= 90:
                color_start = "\033[91m"  # Red
            elif percentage >= 75:
                color_start = "\033[93m"  # Yellow
            else:
                color_start = "\033[92m"  # Green
            color_end = "\033[0m"

            return f"\n{color_start}[{bar}] {percentage:.0f}% | {tokens_display} tokens{color_end}"

        except Exception:
            return ""

    def render_response(self, response: str):
        """Render assistant response.

        Args:
            response: Response text (markdown)
        """
        # Simple formatted output
        print("\n" + "─" * 60)
        print(response)
        print("─" * 60 + "\n")
