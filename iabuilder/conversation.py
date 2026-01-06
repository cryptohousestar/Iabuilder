"""Conversation management with history and persistence."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context_compressor import ContextCompressor
from .debug import debug, debug_message, debug_separator


class Conversation:
    """Manages conversation messages and history."""

    def __init__(
        self,
        history_dir: Optional[Path] = None,
        session_id: Optional[str] = None,
        auto_save: bool = True,
        enable_compression: bool = True,
        project_context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize conversation manager.

        Args:
            history_dir: Directory to store conversation history
            session_id: Session identifier (defaults to timestamp)
            auto_save: Automatically save after each message
            enable_compression: Enable automatic context compression
            project_context: Project context from ProjectExplorer
        """
        self.history_dir = history_dir or (Path.home() / ".iabuilder" / "history")
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = self.history_dir / f"session_{self.session_id}.json"

        self.messages: List[Dict[str, Any]] = []
        self.auto_save = auto_save
        self.enable_compression = enable_compression
        self.compressor = ContextCompressor() if enable_compression else None
        self.compression_count = 0
        self.project_context = project_context

        self.metadata = {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "compression_enabled": enable_compression,
            "compression_count": 0,
        }

        # Build system prompt with project context
        system_prompt = self._build_system_prompt(project_context)

        self.add_message("system", system_prompt)

    def _build_system_prompt(self, project_context: Optional[Dict[str, Any]] = None) -> str:
        """Build the system prompt with optional project context.

        Args:
            project_context: Project context from ProjectExplorer

        Returns:
            Complete system prompt string
        """
        # Get project info
        wd = "directorio actual"
        langs = "todos los lenguajes"
        toolbox_enabled = True  # Default to enabled

        if project_context:
            wd = project_context.get("working_directory", wd)
            detected = project_context.get("languages", [])
            if detected:
                langs = ", ".join(sorted(detected))
            toolbox_enabled = project_context.get("toolbox_enabled", True)

        # Prompt WITHOUT tools (chat mode) - simple and short
        if not toolbox_enabled:
            return f"""Eres un programador experto y asistente útil. Dominas: {langs}.

📍 Proyecto: {wd}

Ayuda con preguntas de programación, explicaciones, debugging y consejos técnicos.
Si el usuario necesita ejecutar comandos, sugiérele activar Toolbox con /toolbox."""

        # Prompt WITH tools (full mode) - inspired by Gemini CLI best practices
        return f"""Eres un agente CLI especializado en ingeniería de software. Dominas: {langs}.

📍 DIRECTORIO: {wd}

═══════════════════════════════════════════════════════════
⚡ PRINCIPIO FUNDAMENTAL: USA HERRAMIENTAS, NO TEXTO
═══════════════════════════════════════════════════════════

• USA herramientas para ACCIONES (ejecutar, leer, escribir, buscar)
• USA texto SOLO para comunicarte con el usuario
• NUNCA describas qué VAS a hacer → HAZLO directamente
• NUNCA simules resultados → USA las herramientas reales

═══════════════════════════════════════════════════════════
🔧 HERRAMIENTAS DISPONIBLES
═══════════════════════════════════════════════════════════

• execute_bash: Comandos shell (ls, npm, git, python, cat, grep, etc.)
• read_file: Lee contenido de archivos
• write_file: Crea archivos nuevos
• edit_file: Modifica archivos existentes (buscar y reemplazar)
• web_search: Busca información en internet

═══════════════════════════════════════════════════════════
📋 FLUJO DE TRABAJO
═══════════════════════════════════════════════════════════

1. ENTENDER: Lee la solicitud
2. ACTUAR: Usa herramientas inmediatamente (sin pedir confirmación)
3. VERIFICAR: Si falla, analiza el error y reintenta
4. REPORTAR: Comunica el resultado brevemente

ERRORES: Si una herramienta falla:
→ Lee el error → Busca la ruta correcta con ls → Reintenta
→ NUNCA abandones en el primer intento

═══════════════════════════════════════════════════════════
✅ COMPORTAMIENTO ESPERADO
═══════════════════════════════════════════════════════════

Usuario: "analiza el proyecto"
→ EJECUTA: ls, read_file de archivos clave (package.json, setup.py, etc.)
→ NO DIGAS: "Voy a analizar..." → HAZLO

Usuario: "arregla el error en X"
→ EJECUTA: read_file X, identifica error, edit_file para corregir
→ NO DIGAS: "Primero necesito..." → LEE Y ARREGLA

Usuario: "crea un archivo Y"
→ EJECUTA: write_file Y con el contenido apropiado
→ NO DIGAS: "¿Qué contenido quieres?" → USA tu conocimiento

═══════════════════════════════════════════════════════════
📋 PLANIFICACIÓN Y EJECUCIÓN
═══════════════════════════════════════════════════════════

Para tareas complejas, sigue este formato:

**ANÁLISIS:**
- [ ] Punto 1 a investigar
- [ ] Punto 2 a investigar

**IMPLEMENTACIÓN:**
- [ ] Cambio 1 a realizar
- [ ] Cambio 2 a realizar

Luego EJECUTA cada punto en orden, marcando [x] cuando completes.

NUNCA preguntes "¿Procedo?" - PLANIFICA y ACTÚA directamente

═══════════════════════════════════════════════════════════
💬 COMUNICACIÓN
═══════════════════════════════════════════════════════════

• Respuestas CONCISAS (menos de 3 líneas cuando sea posible)
• Responde en ESPAÑOL
• NO uses emojis excesivos
• Formato CLI: directo y al punto

═══════════════════════════════════════════════════════════
🚫 ERRORES COMUNES A EVITAR
═══════════════════════════════════════════════════════════

NUNCA escribas esto como texto:
• "[Acción: ejecuté X]" ← INCORRECTO - es texto, no herramienta
• "```tool_code ... ```" ← INCORRECTO - usa function calling nativo
• "print(default_api.X())" ← INCORRECTO - invoca la herramienta directamente

CORRECTO: Simplemente INVOCA la herramienta usando function calling.
El sistema te mostrará el resultado automáticamente.

═══════════════════════════════════════════════════════════
📢 SIEMPRE REPORTA TU PROGRESO
═══════════════════════════════════════════════════════════

Cuando termines de usar herramientas, SIEMPRE comunica al usuario:
• Qué encontraste o qué resultado obtuviste
• Qué cambios hiciste
• Si hay algún problema o siguiente paso

EJEMPLO después de ejecutar herramientas:
"Encontré 3 archivos TypeScript. El error está en `utils.ts` línea 42.
Ya lo corregí cambiando X por Y."

NUNCA te detengas en silencio - el usuario necesita saber qué pasó."""

    def _format_project_context(self, ctx: Dict[str, Any]) -> str:
        """Format project context for system prompt - minimal version.

        Args:
            ctx: Project context dictionary

        Returns:
            Formatted project context string (compact)
        """
        parts = []

        # Directory (essential)
        if ctx.get("working_directory"):
            parts.append(f"Dir: {ctx['working_directory']}")

        # Languages (compact)
        if ctx.get("languages"):
            parts.append(f"Lang: {', '.join(sorted(ctx['languages']))}")

        return " | ".join(parts) if parts else ""

    def add_message(
        self,
        role: str,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        name: Optional[str] = None,
    ):
        """Add a message to the conversation.

        Args:
            role: Message role (user, assistant, tool, system)
            content: Message content
            tool_calls: Tool calls (for assistant messages)
            tool_call_id: Tool call ID (for tool messages)
            name: Tool name (for tool messages)
        """
        # Check if compression is needed before adding the message
        if (
            self.enable_compression
            and self.compressor
            and self.compressor.should_compress(self)
        ):
            self._perform_compression()

        message: Dict[str, Any] = {"role": role}

        if content is not None:
            message["content"] = content

        if tool_calls:
            # Convert tool calls to dictionaries for JSON serialization
            debug("context", f"Saving {len(tool_calls)} tool_calls to conversation")
            serializable_tool_calls = []
            for tc in tool_calls:
                if isinstance(tc, dict):
                    # Already a dictionary (from streaming) - use as-is
                    serializable_tool_calls.append(tc)
                    tc_name = tc.get("function", {}).get("name", "unknown")
                    debug("context", f"  Saved dict tool_call: {tc_name}", indent=1)
                elif hasattr(tc, "model_dump"):  # Pydantic models
                    serializable_tool_calls.append(tc.model_dump())
                    debug("context", f"  Saved pydantic tool_call: {getattr(tc, 'function', {})}", indent=1)
                elif hasattr(tc, "dict"):  # Older Pydantic versions
                    serializable_tool_calls.append(tc.dict())
                    debug("context", f"  Saved old pydantic tool_call", indent=1)
                else:
                    # Manual conversion for SDK objects (Groq, OpenAI, etc.)
                    try:
                        func = getattr(tc, 'function', None)
                        tool_call_dict = {
                            "id": getattr(tc, "id", "") or "",
                            "type": getattr(tc, "type", "function") or "function",
                            "function": {
                                "name": getattr(func, "name", "") if func else "",
                                "arguments": getattr(func, "arguments", "") if func else "",
                            },
                        }
                        serializable_tool_calls.append(tool_call_dict)
                        debug("context", f"  Saved SDK object tool_call: {tool_call_dict['function']['name']}", indent=1)
                    except Exception as e:
                        # Last resort fallback
                        debug("context", f"  ERROR saving tool_call: {e}, type={type(tc)}", indent=1)
                        serializable_tool_calls.append({"error": str(tc)})
            message["tool_calls"] = serializable_tool_calls

        if tool_call_id:
            message["tool_call_id"] = tool_call_id

        if name:
            message["name"] = name

        message["timestamp"] = datetime.now().isoformat()

        self.messages.append(message)

        if self.auto_save:
            self.save()

    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation messages.

        Args:
            limit: Maximum number of recent messages to return

        Returns:
            List of message dictionaries
        """
        if limit is None:
            return self.messages.copy()
        return self.messages[-limit:]

    def get_messages_for_api(self, convert_tool_to_user: bool = True) -> List[Dict[str, Any]]:
        """Get messages formatted for API.

        Removes timestamp and handles tool messages for compatibility
        with different providers (OpenAI, Gemini, etc.).

        Args:
            convert_tool_to_user: If True, convert tool-related messages to
                                  user/assistant messages for broader compatibility

        Returns:
            List of messages ready for API
        """
        debug("context", f"Building API messages (convert_tool_to_user={convert_tool_to_user})")
        debug("context", f"  Format: {'TEXT (user/assistant)' if convert_tool_to_user else 'NATIVE (tool_calls/tool)'}")

        api_messages = []
        for msg in self.messages:
            # Remove timestamp
            api_msg = {k: v for k, v in msg.items() if k != "timestamp"}
            role = api_msg.get("role")

            # Handle assistant messages with tool_calls
            if role == "assistant" and api_msg.get("tool_calls"):
                if convert_tool_to_user:
                    # Convert to simple assistant message describing the action
                    tool_calls = api_msg.get("tool_calls", [])
                    tool_descriptions = []
                    for tc in tool_calls:
                        name, args = self._extract_tool_info(tc)
                        # Truncate args for readability
                        args_preview = args[:100] + "..." if len(args) > 100 else args
                        tool_descriptions.append(f"Ejecuté {name}({args_preview})")
                        debug("context", f"  Tool call: {name}", indent=1)

                    content = api_msg.get("content") or ""
                    action_text = "\n".join(tool_descriptions)
                    # Use past tense format that doesn't look like a command
                    full_content = f"{content}\n(Herramienta usada: {action_text})" if content else f"(Herramienta usada: {action_text})"

                    api_messages.append({
                        "role": "assistant",
                        "content": full_content
                    })
                else:
                    # Keep original format with tool_calls
                    api_messages.append(api_msg)

            # Handle tool result messages
            elif role == "tool":
                if convert_tool_to_user:
                    # Convert to user message for universal compatibility
                    tool_name = api_msg.get("name", "tool")
                    content = api_msg.get("content", "{}")
                    # Truncate long results for context efficiency
                    if len(content) > 2000:
                        content = content[:2000] + "\n... [resultado truncado]"
                    user_msg = {
                        "role": "user",
                        "content": f"[Resultado de {tool_name}]:\n{content}"
                    }
                    api_messages.append(user_msg)
                    debug("context", f"  Tool result: {tool_name} ({len(content)} chars)", indent=1)
                else:
                    # Keep OpenAI format
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": api_msg.get("tool_call_id", "unknown"),
                        "content": api_msg.get("content", "{}"),
                    }
                    if "name" in api_msg:
                        tool_msg["name"] = api_msg["name"]
                    api_messages.append(tool_msg)
            else:
                api_messages.append(api_msg)

        debug("context", f"Built {len(api_messages)} messages for API")
        return api_messages

    def _extract_tool_info(self, tc) -> tuple:
        """Extract tool name and arguments from various formats.

        Handles:
        - OpenAI format: {id, function: {name, arguments}}
        - Gemini format: {name, args}
        - Object format with attributes

        Args:
            tc: Tool call in any format

        Returns:
            Tuple of (name, arguments_string)
        """
        name = "unknown"
        args = "{}"

        debug("context", f"Extracting tool info from type={type(tc).__name__}")

        try:
            if isinstance(tc, dict):
                debug("context", f"  Dict keys: {list(tc.keys())}", indent=1)
                # Try OpenAI format first: {function: {name, arguments}}
                if "function" in tc:
                    func = tc["function"]
                    if isinstance(func, dict):
                        name = func.get("name", "unknown")
                        args = func.get("arguments", "{}")
                        debug("context", f"  OpenAI dict format -> {name}", indent=1)
                    else:
                        name = getattr(func, 'name', 'unknown')
                        args = getattr(func, 'arguments', '{}')
                        debug("context", f"  OpenAI object format -> {name}", indent=1)
                # Try Gemini format: {name, args}
                elif "name" in tc:
                    name = tc.get("name", "unknown")
                    args_val = tc.get("args", tc.get("arguments", {}))
                    if isinstance(args_val, dict):
                        args = json.dumps(args_val, ensure_ascii=False)
                    else:
                        args = str(args_val) if args_val else "{}"
                    debug("context", f"  Gemini format -> {name}", indent=1)
                # Check for error format (from failed save)
                elif "error" in tc:
                    debug("context", f"  ERROR format detected: {tc.get('error', '')[:50]}", indent=1)
                else:
                    debug("context", f"  Unknown dict format, keys: {list(tc.keys())}", indent=1)
            elif isinstance(tc, str):
                # String format - this is the bug we fixed
                debug("context", f"  STRING format (BUG): {tc[:50]}", indent=1)
            else:
                # Object format
                if hasattr(tc, 'function') and tc.function:
                    name = getattr(tc.function, 'name', 'unknown')
                    args = getattr(tc.function, 'arguments', '{}')
                    debug("context", f"  SDK object format -> {name}", indent=1)
                elif hasattr(tc, 'name'):
                    name = getattr(tc, 'name', 'unknown')
                    args_val = getattr(tc, 'args', getattr(tc, 'arguments', {}))
                    if isinstance(args_val, dict):
                        args = json.dumps(args_val, ensure_ascii=False)
                    else:
                        args = str(args_val) if args_val else "{}"
                    debug("context", f"  Direct name format -> {name}", indent=1)
                else:
                    debug("context", f"  Unknown object format: {type(tc)}", indent=1)
        except Exception as e:
            debug("context", f"Error extracting tool info: {e}")

        return name, args

    def clear(self):
        """Clear all messages from conversation."""
        self.messages = []
        if self.auto_save:
            self.save()

    def _perform_compression(self):
        """Perform automatic context compression."""
        if not self.compressor:
            return

        try:
            result = self.compressor.compress_conversation(self)

            # Update messages with compressed version
            self.messages = result["truncated_messages"]
            self.compression_count += 1

            # Update metadata
            self.metadata["compression_count"] = self.compression_count
            self.metadata["last_compression"] = datetime.now().isoformat()
            self.metadata["original_tokens"] = result["original_tokens"]
            self.metadata["compressed_messages"] = result["compressed_messages"]

        except Exception as e:
            print(f"Warning: Context compression failed: {e}")
            # Continue without compression if it fails

    def save(self, file_path: Optional[Path] = None):
        """Save conversation to file.

        Args:
            file_path: Custom file path (defaults to session file)
        """
        save_path = file_path or self.session_file

        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["message_count"] = len(self.messages)
        self.metadata["compression_count"] = self.compression_count
        self.metadata["compression_enabled"] = self.enable_compression

        # Estimate current token count
        if self.compressor:
            self.metadata["current_tokens"] = (
                self.compressor.estimate_conversation_tokens(self.messages)
            )

        data = {
            "session_id": self.session_id,
            "metadata": self.metadata,
            "messages": self.messages,
        }

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, file_path: Optional[Path] = None) -> bool:
        """Load conversation from file.

        Args:
            file_path: File path to load from (defaults to session file)

        Returns:
            True if loaded successfully, False otherwise
        """
        load_path = file_path or self.session_file

        if not load_path.exists():
            return False

        try:
            with open(load_path) as f:
                data = json.load(f)

            self.session_id = data.get("session_id", self.session_id)
            self.metadata = data.get("metadata", {})
            self.messages = data.get("messages", [])

            return True

        except Exception:
            return False

    def export_markdown(self, file_path: Path):
        """Export conversation to Markdown format.

        Args:
            file_path: Path to export file
        """
        lines = []
        lines.append(f"# IABuilder Conversation\n")
        lines.append(f"**Session ID:** {self.session_id}\n")
        lines.append(f"**Created:** {self.metadata.get('created_at', 'Unknown')}\n")
        lines.append(f"**Messages:** {len(self.messages)}\n")
        lines.append("\n---\n\n")

        for msg in self.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            lines.append(f"## {role.upper()}\n")
            if timestamp:
                lines.append(f"*{timestamp}*\n\n")

            if content:
                lines.append(f"{content}\n\n")

            # Handle tool calls
            if "tool_calls" in msg and msg["tool_calls"]:
                lines.append("**Tool Calls:**\n")
                for tc in msg["tool_calls"]:
                    func_name = "unknown"
                    func_args = "{}"
                    if isinstance(tc, str):
                        func_name = tc
                    elif isinstance(tc, dict):
                        func_name = tc.get("function", {}).get("name", "unknown")
                        func_args = tc.get("function", {}).get("arguments", "{}")
                    elif hasattr(tc, 'function'):
                        func = getattr(tc, 'function', None)
                        if func:
                            func_name = getattr(func, 'name', 'unknown')
                            func_args = getattr(func, 'arguments', '{}')
                    lines.append(f"- `{func_name}({func_args})`\n")
                lines.append("\n")

            lines.append("---\n\n")

        with open(file_path, "w") as f:
            f.writelines(lines)

    def get_token_estimate(self) -> int:
        """Estimate token count for conversation.

        This is a rough estimate: ~4 characters per token.

        Returns:
            Estimated token count
        """
        total_chars = 0
        for msg in self.messages:
            content = msg.get("content", "")
            if content:
                total_chars += len(content)

            # Add tool call content
            if "tool_calls" in msg:
                for tc in msg["tool_calls"]:
                    total_chars += len(json.dumps(tc))

        return total_chars // 4

    def get_context_status(self, max_context: int = 128000) -> Dict[str, Any]:
        """Get context usage status for display.

        Args:
            max_context: Maximum context window for the model (default 128K)

        Returns:
            Dictionary with context usage info
        """
        current_tokens = self.get_token_estimate()
        percentage = (current_tokens / max_context) * 100 if max_context > 0 else 0

        # Determine warning level
        if percentage >= 90:
            level = "critical"
            warning = "⚠️  CONTEXTO CRÍTICO: Usa /compress para continuar"
        elif percentage >= 75:
            level = "warning"
            warning = "⚠️  Contexto alto: Considera usar /compress"
        elif percentage >= 50:
            level = "notice"
            warning = None
        else:
            level = "ok"
            warning = None

        return {
            "current_tokens": current_tokens,
            "max_tokens": max_context,
            "percentage": percentage,
            "level": level,
            "warning": warning,
            "messages_count": len(self.messages),
        }

    def truncate_to_limit(self, max_tokens: int, keep_system: bool = True):
        """Truncate conversation to fit within token limit.

        Keeps most recent messages and optionally system messages.

        Args:
            max_tokens: Maximum token limit
            keep_system: Keep system messages at the beginning
        """
        system_messages = []
        other_messages = []

        for msg in self.messages:
            if msg.get("role") == "system" and keep_system:
                system_messages.append(msg)
            else:
                other_messages.append(msg)

        # Estimate tokens for system messages
        system_tokens = sum(len(msg.get("content", "")) // 4 for msg in system_messages)

        available_tokens = max_tokens - system_tokens

        # Add messages from the end until we hit the limit
        truncated_messages = []
        current_tokens = 0

        for msg in reversed(other_messages):
            msg_tokens = len(msg.get("content", "")) // 4
            if "tool_calls" in msg:
                msg_tokens += len(json.dumps(msg["tool_calls"])) // 4

            if current_tokens + msg_tokens > available_tokens:
                break

            truncated_messages.insert(0, msg)
            current_tokens += msg_tokens

        self.messages = system_messages + truncated_messages

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all saved conversation sessions.

        Returns:
            List of session metadata dictionaries
        """
        sessions = []

        for session_file in self.history_dir.glob("session_*.json"):
            try:
                with open(session_file, encoding="utf-8") as f:
                    data = json.load(f)

                metadata = data.get("metadata", {})
                sessions.append(
                    {
                        "file": session_file.name,
                        "session_id": data.get("session_id"),
                        "created_at": metadata.get("created_at"),
                        "last_updated": metadata.get("last_updated"),
                        "message_count": metadata.get("message_count", 0),
                        "compression_count": metadata.get("compression_count", 0),
                        "compression_enabled": metadata.get(
                            "compression_enabled", False
                        ),
                        "current_tokens": metadata.get("current_tokens", 0),
                        "original_tokens": metadata.get("original_tokens"),
                    }
                )
            except Exception:
                continue

        return sorted(sessions, key=lambda x: x.get("last_updated", ""), reverse=True)

    def list_compressed_sessions(self) -> List[Dict[str, Any]]:
        """List all compressed conversation sessions.

        Returns:
            List of compressed session metadata dictionaries
        """
        if not self.compressor:
            return []

        return self.compressor.list_compressed_sessions()

    def load_compressed_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a compressed conversation session.

        Args:
            session_id: Session ID to load

        Returns:
            Compressed session data or None if not found
        """
        if not self.compressor:
            return None

        return self.compressor.load_compressed_session(session_id)

    def add_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: Dict[str, Any],
    ):
        """Add a tool execution result to the conversation.

        Args:
            tool_call_id: ID of the tool call this result corresponds to
            tool_name: Name of the tool that was executed
            result: Result dictionary from tool execution
        """
        message: Dict[str, Any] = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": json.dumps(result, ensure_ascii=False),
            "timestamp": datetime.now().isoformat(),
        }

        self.messages.append(message)

        if self.auto_save:
            self.save()

    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics for this conversation.

        Returns:
            Dictionary with compression statistics
        """
        if not self.compressor:
            return {"compression_enabled": False}

        current_tokens = self.compressor.estimate_conversation_tokens(self.messages)

        return {
            "compression_enabled": True,
            "compression_count": self.compression_count,
            "current_tokens": current_tokens,
            "max_tokens": self.compressor.max_tokens,
            "compression_threshold": self.compressor.compression_threshold,
            "should_compress": self.compressor.should_compress(self),
            "compression_ratio": self.metadata.get("original_tokens", current_tokens)
            / current_tokens
            if current_tokens > 0
            else 1.0,
        }
