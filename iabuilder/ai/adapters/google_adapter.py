"""Google/Gemini family adapter.

Handles: Gemini 1.x, Gemini 2.x, Gemini 3.x (future)
Based on Gemini CLI best practices.
"""

import json
import re
from typing import Any, Dict, List, Optional

from .base import AbstractAdapter, ToolCall, ParsedResponse
from ...debug import debug, debug_adapter, debug_tool_call


class GoogleAdapter(AbstractAdapter):
    """Adapter for Google Gemini models.

    Gemini has some quirks with tool calling:
    - Sometimes outputs tool_code blocks instead of native function calls
    - Uses {name, args} format instead of {function: {name, arguments}}
    - May need explicit instructions to use native function calling
    """

    family_name = "google"
    support_level = "compatible"
    model_patterns = ["gemini", "google/gemini", "palm", "bard"]

    supports_tools = True
    supports_parallel_tools = True
    supports_streaming = True
    supports_native_tool_messages = True  # Gemini via OpenRouter supports native tool message format

    # Patterns for parsing tool_code blocks
    TOOL_CODE_BLOCK_PATTERN = re.compile(
        r'```tool_code\s*\n(.*?)```',
        re.DOTALL | re.IGNORECASE
    )

    PYTHON_BLOCK_PATTERN = re.compile(
        r'```python\s*\n(.*?)```',
        re.DOTALL | re.IGNORECASE
    )

    # Patterns to extract function calls from tool_code
    TOOL_CODE_CALL_PATTERNS = [
        # print(default_api.func(...))
        re.compile(r'print\s*\(\s*default_api\.(\w+)\s*\(\s*(.*?)\s*\)\s*\)', re.DOTALL),
        # default_api.func(...)
        re.compile(r'default_api\.(\w+)\s*\(\s*(.*?)\s*\)', re.DOTALL),
        # Direct call for known tools
        re.compile(
            r'\b(read_file|write_file|edit_file|execute_bash)\s*\(\s*(.*?)\s*\)',
            re.DOTALL
        ),
    ]

    # Pattern for cleaning tool_code blocks
    TOOL_CODE_CLEAN_PATTERN = re.compile(
        r'```(?:tool_code|python)\s*\n(?:.*?default_api\.|.*?(?:read_file|write_file|edit_file|execute_bash)\s*\().*?```',
        re.DOTALL | re.IGNORECASE
    )

    # Pattern for cleaning fake tool_outputs (hallucinated responses)
    TOOL_OUTPUTS_CLEAN_PATTERN = re.compile(
        r'```tool_outputs?\s*\n.*?```',
        re.DOTALL | re.IGNORECASE
    )

    # Known tool names for detection (5 essential tools)
    KNOWN_TOOLS = [
        'read_file', 'write_file', 'edit_file', 'execute_bash', 'web_search',
    ]

    def get_system_prompt_additions(self) -> str:
        """Add Gemini-specific instructions for better tool usage."""
        debug("adapters", "Adding Gemini-specific system prompt instructions")
        return """
═══════════════════════════════════════════════════════════
🔧 INSTRUCCIONES ESPECÍFICAS PARA GEMINI
═══════════════════════════════════════════════════════════

IMPORTANTE: Usa el mecanismo NATIVO de function calling.
• NO escribas bloques ```tool_code``` o ```python``` para llamar funciones
• INVOCA las herramientas directamente usando la interfaz de function calling
• Cuando necesites ejecutar un comando, usa execute_bash directamente
• Cuando necesites leer un archivo, usa read_file directamente

NUNCA hagas esto:
```tool_code
print(default_api.execute_bash(command="ls"))
```

EN VEZ, simplemente invoca la herramienta execute_bash con los argumentos.
"""

    def parse_native_tool_calls(self, response: Any) -> List[ToolCall]:
        """Parse Gemini tool calls.

        Gemini can return tool calls in multiple formats:
        1. OpenAI-compatible (through OpenRouter): {function: {name, arguments}}
        2. Gemini native: {name, args}
        3. Direct function_call attribute
        """
        debug("adapters", "GoogleAdapter: Parsing native tool calls")
        tool_calls = []

        try:
            # Try OpenAI-compatible format first (from OpenRouter)
            if hasattr(response, 'choices') and response.choices:
                message = response.choices[0].message

                if hasattr(message, 'tool_calls') and message.tool_calls:
                    debug("adapters", f"Found {len(message.tool_calls)} tool_calls in OpenAI format")
                    for tc in message.tool_calls:
                        tool_call = self._parse_single_tool_call(tc)
                        if tool_call:
                            tool_calls.append(tool_call)
                            debug_tool_call(tool_call.name, tool_call.arguments, tool_call.id)

            # Try Gemini native format
            if not tool_calls:
                debug("adapters", "Trying Gemini native format")
                tool_calls = self._parse_gemini_native(response)

        except Exception as e:
            debug("adapters", f"Error parsing tool calls: {e}")

        debug("adapters", f"Parsed {len(tool_calls)} tool calls total")
        return tool_calls

    def _fix_double_escaped_strings(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fix double-escaped strings in arguments.

        Gemini sometimes outputs double-escaped JSON like:
        - \\\" instead of \"
        - \\n instead of actual newlines

        This method detects and fixes these issues.
        """
        if not args:
            return args

        fixed = {}
        for key, value in args.items():
            if isinstance(value, str):
                # Check if string has double-escaped sequences
                if '\\n' in value or '\\"' in value or '\\t' in value:
                    # Try to unescape: \\n -> \n, \\" -> ", etc.
                    try:
                        # Use encode/decode to handle escape sequences
                        fixed_value = value.encode('utf-8').decode('unicode_escape')
                        fixed[key] = fixed_value
                        debug("adapters", f"Fixed double-escaped string in '{key}'")
                    except Exception:
                        fixed[key] = value
                else:
                    fixed[key] = value
            elif isinstance(value, dict):
                fixed[key] = self._fix_double_escaped_strings(value)
            else:
                fixed[key] = value

        return fixed

    def _parse_single_tool_call(self, tc: Any) -> Optional[ToolCall]:
        """Parse a single tool call from various formats."""
        try:
            # Dict format
            if isinstance(tc, dict):
                # OpenAI format: {id, function: {name, arguments}}
                if "function" in tc:
                    func = tc["function"]
                    tc_id = tc.get("id", "unknown")
                    name = func.get("name", "unknown")
                    args = func.get("arguments", {})
                # Gemini format: {name, args}
                else:
                    tc_id = tc.get("id", tc.get("call_id", "unknown"))
                    name = tc.get("name", "unknown")
                    args = tc.get("args", tc.get("arguments", {}))

                # Parse arguments if string
                if isinstance(args, str):
                    args = json.loads(args) if args else {}

                # Fix double-escaped strings (common Gemini issue)
                args = self._fix_double_escaped_strings(args)

                return ToolCall(id=tc_id, name=name, arguments=args)

            # Object format
            else:
                tc_id = getattr(tc, 'id', getattr(tc, 'call_id', 'unknown'))

                # Check for function attribute (OpenAI style)
                func = getattr(tc, 'function', None)
                if func:
                    name = getattr(func, 'name', 'unknown')
                    args = getattr(func, 'arguments', '{}')
                else:
                    # Direct attributes (Gemini style)
                    name = getattr(tc, 'name', 'unknown')
                    args = getattr(tc, 'args', getattr(tc, 'arguments', {}))

                # Parse arguments if string
                if isinstance(args, str):
                    args = json.loads(args) if args else {}

                # Fix double-escaped strings (common Gemini issue)
                args = self._fix_double_escaped_strings(args)

                return ToolCall(id=tc_id, name=name, arguments=args)

        except Exception:
            return None

    def _parse_gemini_native(self, response: Any) -> List[ToolCall]:
        """Parse native Gemini API format.

        Gemini native format:
        response.candidates[0].content.parts = [
            {functionCall: {name: "tool", args: {...}}}
        ]
        """
        tool_calls = []

        try:
            candidates = getattr(response, 'candidates', [])
            if not candidates:
                return []

            content = getattr(candidates[0], 'content', None)
            if not content:
                return []

            parts = getattr(content, 'parts', [])
            for i, part in enumerate(parts):
                func_call = getattr(part, 'functionCall', None) or getattr(part, 'function_call', None)
                if func_call:
                    name = getattr(func_call, 'name', 'unknown')
                    args = getattr(func_call, 'args', {})

                    if isinstance(args, str):
                        args = json.loads(args) if args else {}

                    tool_calls.append(ToolCall(
                        id=f"gemini_{i}",
                        name=name,
                        arguments=args,
                    ))

        except Exception:
            pass

        return tool_calls

    def parse_fallback_tool_calls(self, content: str) -> List[ToolCall]:
        """Parse tool_code blocks from Gemini responses.

        Gemini often outputs tool calls in this format:
        ```tool_code
        print(default_api.read_file(file_path = "path/to/file"))
        ```
        """
        debug("adapters", "GoogleAdapter: Parsing fallback tool_code blocks")

        if not content:
            debug("adapters", "No content to parse")
            return []

        tool_calls = []
        call_index = 0
        seen = set()

        # Find tool_code blocks (higher priority)
        tool_code_blocks = self.TOOL_CODE_BLOCK_PATTERN.findall(content)

        # Find python blocks that might contain tool calls
        python_blocks = self.PYTHON_BLOCK_PATTERN.findall(content)

        # Process all blocks
        all_blocks = [(block, True) for block in tool_code_blocks]
        all_blocks += [(block, False) for block in python_blocks]

        for block, is_tool_code in all_blocks:
            # For python blocks, only process if it looks like a tool call
            if not is_tool_code:
                has_tool_pattern = (
                    'default_api.' in block or
                    any(tool in block for tool in self.KNOWN_TOOLS)
                )
                if not has_tool_pattern:
                    continue

            # Try each pattern
            for pattern in self.TOOL_CODE_CALL_PATTERNS:
                for match in pattern.finditer(block):
                    func_name = match.group(1)
                    params_str = match.group(2)

                    key = f"{func_name}:{params_str}"
                    if key in seen:
                        continue
                    seen.add(key)

                    try:
                        arguments = self._parse_python_params(params_str)
                        if arguments is not None:
                            tool_calls.append(ToolCall(
                                id=f"toolcode_{call_index}",
                                name=func_name,
                                arguments=arguments,
                            ))
                            debug("adapters", f"Parsed fallback tool: {func_name}")
                            debug_tool_call(func_name, arguments, f"toolcode_{call_index}")
                            call_index += 1
                    except Exception as e:
                        debug("adapters", f"Failed to parse tool_code: {e}")

        debug("adapters", f"Fallback parsing found {len(tool_calls)} tool calls")
        return tool_calls

    def _parse_python_params(self, params_str: str) -> Optional[Dict[str, Any]]:
        """Parse Python-style parameters to dict.

        Converts: 'file_path = "test.js", content = "hello"'
        To: {"file_path": "test.js", "content": "hello"}
        """
        if not params_str.strip():
            return {}

        result = {}

        # Pattern for triple-quoted strings
        triple_pattern = re.compile(
            r'(\w+)\s*=\s*("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')',
            re.DOTALL
        )

        # Pattern for single-line values
        single_pattern = re.compile(
            r'(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\d+(?:\.\d+)?|True|False|None|\{[^}]*\}|\[[^\]]*\])',
            re.DOTALL
        )

        # Process triple-quoted strings first
        processed_str = params_str
        for match in triple_pattern.finditer(params_str):
            param_name = match.group(1)
            param_value = match.group(2)

            if param_value.startswith('"""'):
                result[param_name] = param_value[3:-3]
            elif param_value.startswith("'''"):
                result[param_name] = param_value[3:-3]

            # Remove from string
            processed_str = processed_str.replace(match.group(0), '')

        # Process single values
        for match in single_pattern.finditer(processed_str):
            param_name = match.group(1)
            param_value = match.group(2)

            if param_name in result:
                continue

            try:
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
                    try:
                        result[param_name] = json.loads(param_value)
                    except:
                        result[param_name] = param_value
            except:
                result[param_name] = param_value

        return result if result else None

    def clean_content(self, content: str) -> str:
        """Remove tool_code and fake tool_outputs blocks from content."""
        cleaned = self.TOOL_CODE_CLEAN_PATTERN.sub('', content)
        cleaned = self.TOOL_OUTPUTS_CLEAN_PATTERN.sub('', cleaned)
        return cleaned.strip()

    def get_support_level_for_model(self, model_name: str) -> str:
        """Get support level for specific Gemini model."""
        model_lower = model_name.lower()

        # Gemini 1.5 Pro is most reliable
        if "gemini-1.5-pro" in model_lower:
            return "compatible"

        # Gemini 2.0 Flash - fast but sometimes uses tool_code
        if "gemini-2.0-flash" in model_lower or "gemini-2.0" in model_lower:
            return "compatible"

        # Older Gemini 1.0
        if "gemini-1.0" in model_lower or "gemini-pro" in model_lower:
            return "compatible"

        # Future versions - assume compatible
        if "gemini-3" in model_lower:
            return "compatible"

        return "compatible"
