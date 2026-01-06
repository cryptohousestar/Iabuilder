"""AI response processing for IABuilder."""

import json
import re
import time
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

from ..renderer import Renderer
from ..errors import get_error_handler, APIError
from ..tools import get_tool_registry
from ..debug import (
    debug, debug_separator, debug_tool_call, debug_tool_result,
    debug_api_response, debug_adapter
)

if TYPE_CHECKING:
    from .adapters import AbstractAdapter


class MalformedToolCall:
    """Represents a parsed malformed tool call from content."""

    def __init__(self, name: str, arguments: str, call_id: str = "fallback_1"):
        self.id = call_id
        self.function = self.Function(name, arguments)

    class Function:
        def __init__(self, name: str, arguments: str):
            self.name = name
            self.arguments = arguments


class ResponseProcessor:
    """Processes AI responses and executes tool calls."""

    # Flag to indicate if follow-up LLM call is needed
    NEEDS_FOLLOWUP = "__NEEDS_FOLLOWUP__"

    @staticmethod
    def _get_tool_info(tool_call) -> tuple:
        """Extract tool call info from either dict or object format.

        Handles multiple formats:
        - OpenAI format: {id, function: {name, arguments}}
        - Gemini format: {name, args} or object with .name, .args attributes

        Args:
            tool_call: Tool call as dict or object

        Returns:
            Tuple of (id, name, arguments)
        """
        tc_id = "unknown"
        name = "unknown"
        args = "{}"

        if isinstance(tool_call, dict):
            # Try OpenAI format first
            tc_id = tool_call.get("id", tool_call.get("call_id", "unknown"))
            func = tool_call.get("function", {})

            if isinstance(func, dict) and func:
                name = func.get("name", "unknown")
                args = func.get("arguments", "{}")
            elif func and hasattr(func, 'name'):
                name = getattr(func, 'name', 'unknown')
                args = getattr(func, 'arguments', '{}')
            else:
                # Try Gemini format: {name, args}
                name = tool_call.get("name", "unknown")
                args_val = tool_call.get("args", tool_call.get("arguments", {}))
                if isinstance(args_val, dict):
                    args = json.dumps(args_val)
                else:
                    args = str(args_val) if args_val else "{}"
        else:
            # Object format
            tc_id = getattr(tool_call, 'id', getattr(tool_call, 'call_id', 'unknown'))
            func = getattr(tool_call, 'function', None)

            if func:
                name = getattr(func, 'name', 'unknown')
                args = getattr(func, 'arguments', '{}')
            else:
                # Try direct attributes (Gemini format)
                name = getattr(tool_call, 'name', 'unknown')
                args_val = getattr(tool_call, 'args', getattr(tool_call, 'arguments', {}))
                if isinstance(args_val, dict):
                    args = json.dumps(args_val)
                else:
                    args = str(args_val) if args_val else "{}"

        return tc_id, name, args

    # Patterns to match various malformed tool call formats
    # Format 1: <function=name {...}></function> (with space)
    # Format 2: <function=name{...}></function> (no space)
    # Format 3: <function=name [{...}]></function> (array syntax)
    # Format 4: <function=name {...}/> (self-closing)
    # Format 5: <function=name[]{...}></function> (empty brackets before JSON)
    # Format 6: <function=name({...})></function> (parentheses wrapping JSON)
    MALFORMED_PATTERNS = [
        # With space before JSON object
        re.compile(
            r'<function=(\w+)\s+(\{[^>]+\})(?:>?\s*</function>|/>)',
            re.IGNORECASE | re.DOTALL
        ),
        # No space before JSON object
        re.compile(
            r'<function=(\w+)(\{[^>]+\})(?:>?\s*</function>|/>)',
            re.IGNORECASE | re.DOTALL
        ),
        # Array syntax with space
        re.compile(
            r'<function=(\w+)\s+\[(\{[^>]+\})\](?:>?\s*</function>|/>)',
            re.IGNORECASE | re.DOTALL
        ),
        # Array syntax without space
        re.compile(
            r'<function=(\w+)\[(\{[^>]+\})\](?:>?\s*</function>|/>)',
            re.IGNORECASE | re.DOTALL
        ),
        # Empty brackets before JSON: <function=name[]{...}>
        re.compile(
            r'<function=(\w+)\[\](\{[^>]+\})(?:>?\s*</function>|/>)',
            re.IGNORECASE | re.DOTALL
        ),
        # Parentheses wrapping JSON: <function=name({...})>
        re.compile(
            r'<function=(\w+)\((\{[^)]+\})\)(?:>?\s*</function>|/>)',
            re.IGNORECASE | re.DOTALL
        ),
    ]

    # Combined pattern for cleaning XML-style tool calls from content
    MALFORMED_TOOL_PATTERN = re.compile(
        r'<function=\w+[\s\[\]\(]*\{[^>)]+\}[\s\]\)]*(?:>?\s*</function>|/>)',
        re.IGNORECASE | re.DOTALL
    )

    # Pattern for cleaning tool_code blocks from content
    TOOL_CODE_CLEAN_PATTERN = re.compile(
        r'```(?:tool_code|python)\s*\n(?:.*?default_api\.|.*?(?:read_file|write_file|edit_file|execute_bash|web_search)\s*\().*?```',
        re.DOTALL | re.IGNORECASE
    )

    # Pattern for Gemini-style tool_code blocks (prefer tool_code over generic python)
    # Matches: ```tool_code\n...\n```
    TOOL_CODE_BLOCK_PATTERN = re.compile(
        r'```tool_code\s*\n(.*?)```',
        re.DOTALL | re.IGNORECASE
    )

    # Pattern for python blocks (fallback, used only if contains tool calls)
    PYTHON_BLOCK_PATTERN = re.compile(
        r'```python\s*\n(.*?)```',
        re.DOTALL | re.IGNORECASE
    )

    # Patterns to extract function calls from tool_code blocks
    # Format 1: default_api.function_name(param = "value")
    TOOL_CODE_CALL_PATTERNS = [
        # print(default_api.func(...))
        re.compile(
            r'print\s*\(\s*default_api\.(\w+)\s*\(\s*(.*?)\s*\)\s*\)',
            re.DOTALL
        ),
        # default_api.func(...)
        re.compile(
            r'default_api\.(\w+)\s*\(\s*(.*?)\s*\)',
            re.DOTALL
        ),
        # func(...) - direct call (for known tool names)
        re.compile(
            r'\b(read_file|write_file|edit_file|execute_bash|web_search)\s*\(\s*(.*?)\s*\)',
            re.DOTALL
        ),
    ]

    def __init__(
        self,
        conversation,
        renderer: Optional[Renderer] = None,
        adapter: Optional["AbstractAdapter"] = None
    ):
        """Initialize response processor.

        Args:
            conversation: Conversation manager
            renderer: Renderer for output
            adapter: Optional model family adapter for parsing
        """
        self.conversation = conversation
        self.renderer = renderer or Renderer()
        self.error_handler = get_error_handler()
        self._tool_registry = None  # Will be fetched dynamically
        self.adapter = adapter
        self.tool_confirm_callback = None  # Callback(tool_name, args) -> bool
        self.output_limit_lines = 50  # Max lines to show from tool output

    @property
    def tool_registry(self):
        """Get tool registry dynamically to ensure tools are always available."""
        registry = get_tool_registry()
        # DEBUG: Print when accessed
        # print(f"[DEBUG ResponseProcessor] Accessing tool_registry: {registry.list_tools()}")
        return registry

    def set_adapter(self, adapter: "AbstractAdapter"):
        """Set or update the model adapter.

        Args:
            adapter: Model family adapter
        """
        self.adapter = adapter

    def get_adapter_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current adapter.

        Returns:
            Adapter info dict or None if no adapter set
        """
        if self.adapter:
            return self.adapter.get_model_info()
        return None

    def process_response(self, response, tools: Optional[List] = None) -> str:
        """Process AI response and execute any tool calls.

        If an adapter is set, uses adapter-based parsing for better
        model-specific handling. Otherwise falls back to legacy parsing.

        Args:
            response: AI response object
            tools: Available tools schemas

        Returns:
            Final response text
        """
        debug_separator("tools", "PROCESSING RESPONSE")

        try:
            # Use adapter-based processing if available
            if self.adapter:
                debug_adapter(self.adapter.family_name, "Using adapter", self.adapter.model_name)
                return self._process_with_adapter(response, tools)

            # Legacy processing (fallback)
            debug("tools", "Using legacy processing (no adapter)")
            return self._process_legacy(response, tools)

        except Exception as e:
            debug("tools", f"Error in process_response: {e}")
            self.error_handler.handle_error(
                e,
                context={"phase": "response_processing"}
            )
            return "Lo siento, hubo un error procesando la respuesta."

    def _process_with_adapter(self, response, tools: Optional[List] = None) -> str:
        """Process response using the model adapter.

        Args:
            response: AI response object
            tools: Available tools schemas

        Returns:
            Final response text
        """
        # Parse response with adapter
        parsed = self.adapter.parse_response(response)

        # If we have tool calls, execute them
        if parsed.has_tool_calls:
            # Convert tool_calls to API format for conversation history
            api_tool_calls = [tc.to_api_format() for tc in parsed.tool_calls]

            # Add assistant message WITH tool_calls (required by OpenAI/OpenRouter API)
            self.conversation.add_message(
                "assistant",
                content=parsed.content if parsed.content else None,
                tool_calls=api_tool_calls
            )

            return self._execute_adapter_tool_calls(parsed.tool_calls)

        # No tool calls, just return content
        return parsed.content

    def _truncate_output(self, text: str, max_lines: int = None) -> str:
        """Truncate output to last N lines.

        Args:
            text: Text to truncate
            max_lines: Max lines (defaults to self.output_limit_lines)

        Returns:
            Truncated text with indicator if truncated
        """
        if max_lines is None:
            max_lines = self.output_limit_lines

        if not text:
            return text

        lines = text.split('\n')
        if len(lines) <= max_lines:
            return text

        truncated_count = len(lines) - max_lines
        return f"[... {truncated_count} líneas truncadas ...]\n" + '\n'.join(lines[-max_lines:])

    def _execute_adapter_tool_calls(self, tool_calls: List) -> str:
        """Execute tool calls from adapter parsing.

        Args:
            tool_calls: List of ToolCall objects from adapter

        Returns:
            NEEDS_FOLLOWUP or error message
        """
        executed_count = 0

        for tc in tool_calls:
            try:
                # Check confirmation callback
                if self.tool_confirm_callback:
                    if not self.tool_confirm_callback(tc.name, tc.arguments):
                        self.renderer.render_warning(f"⏭️  Skipped: {tc.name}")
                        self.conversation.add_tool_result(
                            tool_call_id=tc.id,
                            tool_name=tc.name,
                            result={"success": False, "error": "Skipped by user"}
                        )
                        continue

                self.renderer.render_info(f"🔧 Executing: {tc.name}")

                # Execute the tool
                result = self.tool_registry.execute(tc.name, **tc.arguments)

                # Show output in chat (truncated to 50 lines)
                output = result.get("result", result.get("output", ""))
                if output and isinstance(output, str):
                    truncated = self._truncate_output(output)
                    print(f"\033[36m┌─ {tc.name} ─────────────────\033[0m")
                    print(truncated)
                    print(f"\033[36m└{'─' * 35}\033[0m")

                if result.get("success"):
                    executed_count += 1
                    self.renderer.render_success(f"✅ {tc.name} completed")
                else:
                    self.renderer.render_error(
                        f"❌ {tc.name}: {result.get('error', 'Unknown error')}"
                    )

                # Truncate result for conversation (save context)
                if output and isinstance(output, str):
                    result["result"] = self._truncate_output(output)

                # Add tool result to conversation
                self.conversation.add_tool_result(
                    tool_call_id=tc.id,
                    tool_name=tc.name,
                    result=result
                )

                # Small delay between tools
                if len(tool_calls) > 1:
                    time.sleep(0.3)

            except Exception as e:
                self.renderer.render_error(f"❌ Error: {e}")
                self.conversation.add_tool_result(
                    tool_call_id=tc.id,
                    tool_name=tc.name,
                    result={"success": False, "error": str(e)}
                )

        if executed_count > 0:
            return self.NEEDS_FOLLOWUP
        else:
            return "❌ No pude ejecutar las herramientas solicitadas."

    def _detect_hallucinated_blocks(self, content: str) -> Optional[str]:
        """Detect if model is hallucinating tool outputs.

        Args:
            content: Response content to check

        Returns:
            Error message if hallucination detected, None otherwise
        """
        if not content:
            return None

        # Prohibited block patterns (case insensitive)
        prohibited = [
            'tool_outputs',
            'bash_output',
            'tool_result',
            'execution_result',
            'command_output',
            'shell_output',
            '"execute_bash_response"',
            '"read_file_response"',
            '"write_file_response"',
        ]

        content_lower = content.lower()
        for pattern in prohibited:
            if pattern in content_lower:
                return f"⚠️ Formato incorrecto detectado. NUNCA inventes resultados con bloques '{pattern}'. Usa bloques ```tool_code``` para ejecutar comandos REALES."

        return None

    def _process_legacy(self, response, tools: Optional[List] = None) -> str:
        """Legacy response processing (without adapter).

        Args:
            response: AI response object
            tools: Available tools schemas

        Returns:
            Final response text
        """
        # Extract response info for debugging
        has_native_tools = False
        finish_reason = "unknown"
        content_preview = ""

        if hasattr(response, 'choices') and response.choices:
            choice = response.choices[0]
            finish_reason = getattr(choice, 'finish_reason', 'unknown') or 'unknown'
            msg = getattr(choice, 'message', None)
            if msg:
                has_native_tools = bool(getattr(msg, 'tool_calls', None))
                content = getattr(msg, 'content', '') or ''
                content_preview = content[:80].replace('\n', '\\n') if content else "(empty)"

        debug_api_response(bool(content_preview), has_native_tools, finish_reason)
        debug("tools", f"Content preview: {content_preview}")

        # Check if response has proper tool calls
        if self._has_tool_calls(response):
            tool_calls = self._get_tool_calls(response)
            debug("tools", f"Native tool_calls detected: {len(tool_calls)} calls")
            for tc in tool_calls:
                tc_id, tc_name, tc_args = self._get_tool_info(tc)
                debug_tool_call(tc_name, self._safe_parse_args(tc_args), tc_id)
            return self._process_with_tools(response, tools)

        # Check for malformed tool calls in content
        content = self._extract_content(response)
        debug("tools", f"No native tool_calls, checking content for fallback patterns")

        # CRITICAL: Detect hallucinated blocks FIRST
        hallucination_error = self._detect_hallucinated_blocks(content)
        if hallucination_error:
            debug("tools", f"HALLUCINATION DETECTED: {hallucination_error[:50]}")
            self.renderer.render_error(hallucination_error)
            # Add correction message to conversation
            self.conversation.add_message("user", hallucination_error)
            return self.NEEDS_FOLLOWUP  # Force model to retry with correct format

        # First check for Gemini-style tool_code blocks
        tool_code_calls = self._parse_tool_code_blocks(content)
        if tool_code_calls:
            debug("tools", f"Parsed {len(tool_code_calls)} tool_code blocks")
            for tc in tool_code_calls:
                debug_tool_call(tc.function.name, json.loads(tc.function.arguments), tc.id)
            self.renderer.render_info(
                "🔄 Detected tool_code block, executing..."
            )
            return self._process_malformed_tools(tool_code_calls, content)

        # Then check for XML-style malformed tool calls
        malformed_calls = self._parse_malformed_tool_calls(content)
        if malformed_calls:
            debug("tools", f"Parsed {len(malformed_calls)} malformed XML-style calls")
            for tc in malformed_calls:
                debug_tool_call(tc.function.name, json.loads(tc.function.arguments), tc.id)
            self.renderer.render_info(
                "🔄 Detected tool call in response, processing..."
            )
            return self._process_malformed_tools(malformed_calls, content)

        debug("tools", "No tool calls detected, returning content as-is")
        return content

    def _parse_malformed_tool_calls(self, content: str) -> List[MalformedToolCall]:
        """Parse malformed tool calls from response content.

        Handles formats like:
        - <function=execute_bash {"command": "ls"}></function>
        - <function=execute_bash{"command": "ls"}></function>
        - <function=execute_bash [{"command": "ls"}]></function>
        - <function=read_file {"path": "/tmp/test.txt"} />

        Args:
            content: Response content to parse

        Returns:
            List of parsed MalformedToolCall objects
        """
        if not content:
            return []

        calls = []
        seen_calls = set()  # Avoid duplicates
        call_index = 0

        # Try each pattern
        for pattern in self.MALFORMED_PATTERNS:
            matches = pattern.findall(content)

            for func_name, args_str in matches:
                # Create unique key to avoid duplicates
                call_key = f"{func_name}:{args_str}"
                if call_key in seen_calls:
                    continue
                seen_calls.add(call_key)

                try:
                    # Validate JSON arguments
                    json.loads(args_str)
                    calls.append(MalformedToolCall(
                        name=func_name.strip(),
                        arguments=args_str.strip(),
                        call_id=f"malformed_{call_index+1}"
                    ))
                    call_index += 1
                except json.JSONDecodeError:
                    # Try to fix common JSON issues
                    fixed_args = self._fix_json_args(args_str)
                    if fixed_args:
                        calls.append(MalformedToolCall(
                            name=func_name.strip(),
                            arguments=fixed_args,
                            call_id=f"malformed_{call_index+1}"
                        ))
                        call_index += 1

        return calls

    def _parse_tool_code_blocks(self, content: str) -> List[MalformedToolCall]:
        """Parse Gemini-style tool_code blocks from response content.

        Handles formats like:
        ```tool_code
        print(default_api.read_file(file_path = "path/to/file"))
        print(default_api.execute_bash(command = "ls -la"))
        ```

        Or direct shell commands:
        ```tool_code
        ls -la /path/to/dir
        ```

        Args:
            content: Response content to parse

        Returns:
            List of parsed MalformedToolCall objects
        """
        if not content:
            return []

        calls = []
        call_index = 0
        seen_calls = set()  # Avoid duplicates

        # First, find tool_code blocks (higher priority)
        tool_code_blocks = self.TOOL_CODE_BLOCK_PATTERN.findall(content)

        # Then, find python blocks (only if they contain tool patterns)
        python_blocks = self.PYTHON_BLOCK_PATTERN.findall(content)

        # Process tool_code blocks first
        all_blocks = [(block, True) for block in tool_code_blocks]
        all_blocks += [(block, False) for block in python_blocks]

        for block, is_tool_code in all_blocks:
            block = block.strip()
            found_calls = False

            # For python blocks, only process if it looks like a tool call
            if not is_tool_code:
                has_tool_pattern = (
                    'default_api.' in block or
                    any(tool in block for tool in ['read_file', 'write_file', 'edit_file', 'execute_bash', 'web_search'])
                )
                if not has_tool_pattern:
                    continue

            # Try each pattern to find function calls
            for pattern in self.TOOL_CODE_CALL_PATTERNS:
                func_matches = pattern.findall(block)

                for func_name, params_str in func_matches:
                    found_calls = True
                    # Create unique key to avoid duplicates
                    call_key = f"{func_name}:{params_str}"
                    if call_key in seen_calls:
                        continue
                    seen_calls.add(call_key)

                    try:
                        # Convert Python-style params to JSON
                        args_dict = self._parse_python_params(params_str)

                        if args_dict is not None:
                            calls.append(MalformedToolCall(
                                name=func_name.strip(),
                                arguments=json.dumps(args_dict),
                                call_id=f"toolcode_{call_index+1}"
                            ))
                            call_index += 1

                    except Exception as e:
                        # Log but continue
                        pass

            # If no function calls found in tool_code block, treat as direct shell command
            if is_tool_code and not found_calls and block:
                # Check if it looks like a shell command (starts with common commands)
                shell_indicators = ['ls', 'cd', 'cat', 'grep', 'find', 'mkdir', 'rm', 'cp', 'mv',
                                   'pwd', 'echo', 'npm', 'pip', 'python', 'node', 'git', 'docker',
                                   'curl', 'wget', 'chmod', 'chown', 'tar', 'zip', 'unzip']
                first_word = block.split()[0] if block.split() else ''

                if first_word in shell_indicators or '/' in block or block.startswith('./'):
                    call_key = f"execute_bash:{block}"
                    if call_key not in seen_calls:
                        seen_calls.add(call_key)
                        calls.append(MalformedToolCall(
                            name="execute_bash",
                            arguments=json.dumps({"command": block}),
                            call_id=f"toolcode_{call_index+1}"
                        ))
                        call_index += 1

        return calls

    def _parse_python_params(self, params_str: str) -> Optional[Dict[str, Any]]:
        """Parse Python-style function parameters to a dict.

        Converts: 'file_path = "test.js", content = "hello"'
        To: {"file_path": "test.js", "content": "hello"}

        Args:
            params_str: Python-style parameter string

        Returns:
            Dictionary of parameters or None if parsing fails
        """
        if not params_str.strip():
            return {}

        result = {}

        # Pattern for multi-line strings with triple quotes
        triple_quote_pattern = re.compile(
            r'(\w+)\s*=\s*("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')',
            re.DOTALL
        )

        # Pattern for single-line strings and other values
        single_param_pattern = re.compile(
            r'(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\d+(?:\.\d+)?|True|False|None|\{[^}]*\}|\[[^\]]*\])',
            re.DOTALL
        )

        # First, find triple-quoted strings
        triple_matches = triple_quote_pattern.findall(params_str)
        processed_str = params_str

        for param_name, param_value in triple_matches:
            # Remove triple quotes
            if param_value.startswith('"""') and param_value.endswith('"""'):
                result[param_name] = param_value[3:-3]
            elif param_value.startswith("'''") and param_value.endswith("'''"):
                result[param_name] = param_value[3:-3]
            # Remove this match from string to avoid double processing
            processed_str = processed_str.replace(f'{param_name}={param_value}', '')
            processed_str = processed_str.replace(f'{param_name} = {param_value}', '')

        # Then, find single-value parameters
        matches = single_param_pattern.findall(processed_str)

        for param_name, param_value in matches:
            if param_name in result:
                continue  # Already processed as triple-quoted

            # Parse the value
            try:
                # Remove quotes from strings
                if (param_value.startswith('"') and param_value.endswith('"')) or \
                   (param_value.startswith("'") and param_value.endswith("'")):
                    # Handle escape sequences
                    inner = param_value[1:-1]
                    inner = inner.replace('\\n', '\n')
                    inner = inner.replace('\\t', '\t')
                    inner = inner.replace('\\"', '"')
                    inner = inner.replace("\\'", "'")
                    inner = inner.replace('\\\\', '\\')
                    result[param_name] = inner
                elif param_value == 'True':
                    result[param_name] = True
                elif param_value == 'False':
                    result[param_name] = False
                elif param_value == 'None':
                    result[param_name] = None
                elif param_value.replace('.', '').replace('-', '').isdigit():
                    if '.' in param_value:
                        result[param_name] = float(param_value)
                    else:
                        result[param_name] = int(param_value)
                else:
                    # Try to parse as JSON (for dicts/lists)
                    try:
                        result[param_name] = json.loads(param_value)
                    except:
                        result[param_name] = param_value
            except:
                result[param_name] = param_value

        return result if result else None

    def _fix_json_args(self, args_str: str) -> Optional[str]:
        """Try to fix common JSON formatting issues.

        Args:
            args_str: Potentially malformed JSON string

        Returns:
            Fixed JSON string or None if unfixable
        """
        try:
            # Replace single quotes with double quotes
            fixed = args_str.replace("'", '"')
            json.loads(fixed)
            return fixed
        except:
            pass

        try:
            # Try to add missing quotes around keys
            fixed = re.sub(r'(\w+):', r'"\1":', args_str)
            json.loads(fixed)
            return fixed
        except:
            pass

        return None

    def _process_malformed_tools(self, tool_calls: List[MalformedToolCall], original_content: str) -> str:
        """Process malformed tool calls extracted from content.

        Args:
            tool_calls: List of parsed tool calls
            original_content: Original response content

        Returns:
            Result of tool execution
        """
        # Convert malformed tool calls to API format
        api_tool_calls = []
        for tc in tool_calls:
            api_tool_calls.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            })

        # Add assistant message WITH tool_calls (required by OpenAI/OpenRouter API)
        # Clean both XML-style and tool_code blocks from content
        clean_content = self.MALFORMED_TOOL_PATTERN.sub('', original_content)
        clean_content = self.TOOL_CODE_CLEAN_PATTERN.sub('', clean_content).strip()

        self.conversation.add_message(
            "assistant",
            content=clean_content if clean_content else None,
            tool_calls=api_tool_calls
        )

        executed_count = 0
        tool_results = []

        for tool_call in tool_calls:
            try:
                self.renderer.render_info(
                    f"🔧 Executing: {tool_call.function.name}"
                )

                result = self._execute_tool_call(tool_call)

                if result.get("success", False):
                    executed_count += 1

                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.function.name,
                    "result": result
                })

                # Add tool result to conversation
                self.conversation.add_tool_result(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.function.name,
                    result=result
                )

            except Exception as e:
                self.renderer.render_error(f"❌ Error: {e}")
                self.conversation.add_tool_result(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.function.name,
                    result={"success": False, "error": str(e)}
                )

        # Signal that we need a follow-up LLM call to explain results
        if executed_count > 0:
            # Return flag so main loop calls LLM again to explain results
            return self.NEEDS_FOLLOWUP
        else:
            return "❌ No pude ejecutar las herramientas solicitadas."

    def _has_tool_calls(self, response) -> bool:
        """Check if response has tool calls."""
        try:
            # Handle both response.tool_calls and response.choices[0].message.tool_calls
            if hasattr(response, 'choices') and response.choices:
                message = response.choices[0].message
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    return len(message.tool_calls) > 0
            # Fallback for direct tool_calls attribute
            if hasattr(response, "tool_calls") and response.tool_calls:
                return len(response.tool_calls) > 0
            return False
        except:
            return False

    def _get_tool_calls(self, response):
        """Extract tool calls from response."""
        try:
            if hasattr(response, 'choices') and response.choices:
                message = response.choices[0].message
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    return message.tool_calls
            if hasattr(response, "tool_calls") and response.tool_calls:
                return response.tool_calls
            return []
        except:
            return []

    def _process_with_tools(self, response, tools: Optional[List]) -> str:
        """Process response that includes tool calls.

        Args:
            response: AI response with tool calls
            tools: Available tools

        Returns:
            Final response after tool execution
        """
        # First, add the assistant message with tool calls to conversation
        message = response.choices[0].message
        self.conversation.add_message(
            "assistant",
            content=getattr(message, 'content', None),
            tool_calls=self._get_tool_calls(response)
        )

        # Execute tools
        tool_calls = self._get_tool_calls(response)
        executed_count = 0
        tool_results = []

        for tool_call in tool_calls:
            # Extract tool info (handles both dict and object formats)
            tc_id, tc_name, tc_args = self._get_tool_info(tool_call)

            try:
                self.renderer.render_info(f"🔧 Executing: {tc_name}")

                result = self._execute_tool_call_safe(tc_name, tc_args)

                if result.get("success", False):
                    executed_count += 1

                tool_results.append({
                    "tool_call_id": tc_id,
                    "tool_name": tc_name,
                    "result": result
                })

                # Add tool result to conversation
                self.conversation.add_tool_result(
                    tool_call_id=tc_id,
                    tool_name=tc_name,
                    result=result
                )

                # Small delay between tools to prevent rate limiting
                if len(tool_calls) > 1:
                    time.sleep(0.3)

            except Exception as e:
                error_msg = self.error_handler.handle_tool_error(
                    tc_name, e, args=self._safe_parse_args(tc_args)
                )
                self.renderer.render_error(f"❌ {error_msg}")
                # Add error result to conversation
                self.conversation.add_tool_result(
                    tool_call_id=tc_id,
                    tool_name=tc_name,
                    result={"success": False, "error": str(e)}
                )

        # Signal that we need a follow-up LLM call to explain results
        if executed_count > 0:
            return self.NEEDS_FOLLOWUP
        else:
            return "❌ No pude ejecutar las herramientas solicitadas."

    def _execute_tool_call_safe(self, function_name: str, arguments: str) -> Dict[str, Any]:
        """Execute a tool call with pre-extracted info.

        Args:
            function_name: Name of the function to call
            arguments: JSON string of arguments

        Returns:
            Tool execution result
        """
        debug_separator("tools", f"EXECUTING {function_name}")

        try:
            # Parse arguments - handle various formats
            args = {}
            if arguments:
                if isinstance(arguments, dict):
                    args = arguments
                elif isinstance(arguments, str):
                    arguments = arguments.strip()
                    if arguments and arguments != '{}':
                        try:
                            args = json.loads(arguments)
                        except json.JSONDecodeError:
                            # Try to fix common issues
                            debug("tools", f"JSON parse failed, trying to fix quotes")
                            fixed = arguments.replace("'", '"')
                            args = json.loads(fixed)

            debug("tools", f"Parsed args: {list(args.keys())}")

            # Log for debugging if args is empty for tools that require params
            if not args and function_name in ['read_file', 'write_file', 'edit_file', 'execute_bash', 'web_search']:
                debug("tools", f"WARNING: {function_name} called with empty arguments!")
                self.renderer.render_warning(
                    f"⚠️ {function_name} called with empty arguments"
                )

            # Check confirmation callback
            if self.tool_confirm_callback:
                debug("tools", "Waiting for user confirmation...")
                if not self.tool_confirm_callback(function_name, args):
                    debug("tools", "User skipped tool execution")
                    return {"success": False, "error": "Skipped by user"}

            # Execute the tool
            debug("tools", f"Calling tool_registry.execute({function_name}, ...)")
            result = self.tool_registry.execute(function_name, **args)

            # Debug result
            success = result.get("success", False)
            debug_tool_result(function_name, success, result)

            # Show output in chat (truncated to 50 lines)
            output = result.get("result", result.get("output", ""))
            if output and isinstance(output, str):
                truncated = self._truncate_output(output)
                print(f"\033[36m┌─ {function_name} ─────────────────\033[0m")
                print(truncated)
                print(f"\033[36m└{'─' * 35}\033[0m")
                # Truncate for conversation
                result["result"] = truncated

            if result.get("success"):
                self.renderer.render_success(f"✅ {function_name} completed")
            else:
                self.renderer.render_error(
                    f"❌ {function_name}: {result.get('error', 'Unknown error')}"
                )

            return result

        except json.JSONDecodeError as e:
            debug("tools", f"JSONDecodeError: {e}")
            return {
                "success": False,
                "error": f"Invalid arguments: {e}",
                "error_type": "JSONDecodeError"
            }
        except Exception as e:
            debug("tools", f"Exception: {type(e).__name__}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _execute_tool_call(self, tool_call) -> Dict[str, Any]:
        """Execute a single tool call (legacy, uses _get_tool_info)."""
        tc_id, tc_name, tc_args = self._get_tool_info(tool_call)
        return self._execute_tool_call_safe(tc_name, tc_args)

    def _safe_parse_args(self, arguments: str) -> Dict:
        """Parse tool arguments from string safely."""
        try:
            return json.loads(arguments) if arguments else {}
        except:
            return {}

    def _parse_args(self, tool_call) -> Dict:
        """Parse tool call arguments safely (legacy)."""
        tc_id, tc_name, tc_args = self._get_tool_info(tool_call)
        return self._safe_parse_args(tc_args)

    def _extract_content(self, response) -> str:
        """Extract text content from response."""
        try:
            if hasattr(response, 'choices') and response.choices:
                message = response.choices[0].message
                if hasattr(message, 'content') and message.content:
                    return message.content.strip()
            return ""
        except Exception as e:
            self.error_handler.log_warning(f"Could not extract content: {e}")
            return ""


class ToolCallError(Exception):
    """Exception raised when tool call fails but contains extractable tool call."""

    def __init__(self, message: str, failed_generation: str = None):
        super().__init__(message)
        self.failed_generation = failed_generation


class RetryHandler:
    """Handles retries for API calls with exponential backoff."""

    def __init__(self, max_retries: int = 3, base_delay: float = 2.0):
        """Initialize retry handler.

        Args:
            max_retries: Maximum number of retries (default 3 for rate limits)
            base_delay: Base delay in seconds for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.error_handler = get_error_handler()
        self._last_failed_generation = None

    def get_last_failed_generation(self) -> Optional[str]:
        """Get the last failed_generation from a tool_use_failed error."""
        return self._last_failed_generation

    def call_with_retry(self, func, *args, **kwargs):
        """Call function with retry logic.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries fail, or ToolCallError if extractable
        """
        last_error = None
        self._last_failed_generation = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)

            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                error_str = str(e)

                # Check for tool_use_failed errors with extractable tool calls
                if "tool_use_failed" in error_msg and "failed_generation" in error_str:
                    # Extract the failed_generation
                    failed_gen = self._extract_failed_generation(error_str)
                    if failed_gen:
                        self._last_failed_generation = failed_gen
                        # Don't retry - we have the tool call to parse
                        raise ToolCallError(
                            "Tool call format error - extracting from failed_generation",
                            failed_generation=failed_gen
                        )

                # Check if we should retry
                if attempt < self.max_retries:
                    # Rate limit - extract wait time from error if available
                    if "rate limit" in error_msg or "429" in error_msg:
                        # Check if it's a daily limit (TPD) - these require longer waits
                        if "tokens per day" in error_msg or "tpd" in error_msg:
                            # Extract wait time from error message
                            wait_time = self._extract_wait_time(error_str)
                            if wait_time and wait_time > 300:  # More than 5 minutes
                                # Daily limit - show message and don't retry
                                self._wait_with_spinner(60, "Rate limit diario alcanzado")
                                # After short wait, raise error to stop retrying
                                raise Exception(f"Rate limit diario de Groq alcanzado. Intenta de nuevo en {wait_time//60} minutos o usa otro modelo.")

                        delay = int(self.base_delay * (2 ** attempt) * 3)
                        self._wait_with_spinner(delay, "Rate limit reached")
                        continue

                    # Other errors - shorter delay
                    delay = self.base_delay * (2 ** attempt)
                    self.error_handler.log_warning(
                        f"API error, retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue

        # All retries failed
        raise last_error

    def _extract_wait_time(self, error_str: str) -> Optional[int]:
        """Extract wait time in seconds from rate limit error message.

        Args:
            error_str: Error message string

        Returns:
            Wait time in seconds or None if not found
        """
        try:
            # Look for patterns like "34m50.88s" or "5m30s"
            match = re.search(r'(\d+)m(\d+(?:\.\d+)?)?s', error_str)
            if match:
                minutes = int(match.group(1))
                seconds = float(match.group(2)) if match.group(2) else 0
                return int(minutes * 60 + seconds)

            # Look for patterns like "60s" or "30.5s"
            match = re.search(r'(\d+(?:\.\d+)?)s', error_str)
            if match:
                return int(float(match.group(1)))

            return None
        except Exception:
            return None

    def _wait_with_spinner(self, seconds: int, message: str = "Waiting"):
        """Wait with an animated spinner countdown.

        Args:
            seconds: Number of seconds to wait
            message: Message to display
        """
        try:
            from rich.status import Status
            from rich.console import Console

            console = Console()

            with console.status(
                f"[yellow]⏳ {message}. Waiting {seconds}s...[/yellow]",
                spinner="dots"
            ) as status:
                for i in range(seconds, 0, -1):
                    status.update(f"[yellow]⏳ {message}. Waiting {i}s...[/yellow]")
                    time.sleep(1)

        except ImportError:
            # Fallback without Rich
            import sys
            for i in range(seconds, 0, -1):
                sys.stdout.write(f"\r⏳ {message}. Waiting {i}s...  ")
                sys.stdout.flush()
                time.sleep(1)
            print("\r" + " " * 40 + "\r", end="", flush=True)

    def _extract_failed_generation(self, error_str: str) -> Optional[str]:
        """Extract the failed_generation content from an error message.

        Args:
            error_str: Full error string

        Returns:
            The failed_generation content or None
        """
        try:
            # Try to find 'failed_generation': '...' pattern
            import re

            # Pattern for 'failed_generation': '...'
            pattern = r"'failed_generation':\s*'([^']+)'"
            match = re.search(pattern, error_str)
            if match:
                return match.group(1).replace("\\'", "'").replace("\\\"", '"')

            # Pattern for "failed_generation": "..."
            pattern2 = r'"failed_generation":\s*"([^"]+)"'
            match2 = re.search(pattern2, error_str)
            if match2:
                return match2.group(1).replace("\\\"", '"')

            return None
        except Exception:
            return None
