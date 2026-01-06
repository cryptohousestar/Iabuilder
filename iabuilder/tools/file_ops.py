"""File operation tools for reading, writing, and editing files."""
import os
from pathlib import Path
from typing import Dict, Any

from .base import Tool


class ReadFileTool(Tool):
    """Tool for reading file contents with intelligent path resolution."""

    def __init__(self, project_context: Dict[str, Any] = None):
        """Initialize with project context for intelligent path resolution.

        Args:
            project_context: Project context from ProjectExplorer for resolving references
        """
        self.project_context = project_context or {}
        super().__init__()

    def _get_name(self) -> str:
        return "read_file"

    def _get_description(self) -> str:
        description = "📖 READ FILE CONTENTS: Use this to view the contents of existing files. Perfect for examining code, config files, or any text document."

        # Add context-aware hints
        if self.project_context:
            hints = []
            if ".html" in self.project_context.get("file_index", {}):
                hints.append('Use "index.html" or "main.html" for HTML files')
            if ".py" in self.project_context.get("file_index", {}):
                hints.append('Use "main.py" or "app.py" for Python files')
            if self.project_context.get("has_readme"):
                hints.append(f'Use "{self.project_context["has_readme"]}" for documentation')

            if hints:
                description += f"\n\n💡 Context hints:\n" + "\n".join(f"- {hint}" for hint in hints)

        return description

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read (absolute, relative, or reference like 'index.html', 'readme')",
                },
                "start_line": {
                    "type": "integer",
                    "description": "Starting line number (1-indexed, default: 1)",
                    "default": 1,
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ending line number (-1 for end of file, default: -1)",
                    "default": -1,
                },
            },
            "required": ["file_path"],
        }

    def _resolve_file_reference(self, file_reference: str) -> Path:
        """Resolve intelligent file references like Zed does.

        Args:
            file_reference: User input (could be "index.html", "readme", etc.)

        Returns:
            Resolved Path object
        """
        # First, try intelligent resolution using project context
        if self.project_context:
            resolved = self._resolve_intelligent_reference(file_reference)
            if resolved:
                return resolved

        # Then try literal paths
        path = Path(file_reference).expanduser()
        if path.exists():
            return path.resolve()

        # Try relative to current directory
        cwd_path = Path.cwd() / file_reference
        if cwd_path.exists():
            return cwd_path.resolve()

        # If nothing found, return the original path (will fail later with proper error)
        return path

    def _resolve_intelligent_reference(self, file_reference: str) -> Path:
        """Resolve intelligent references like 'el archivo html', 'readme', etc."""
        if not self.project_context:
            return None

        file_index = self.project_context.get("file_index", {})

        # Resolve common references
        if file_reference.lower() in ["readme", "readme.md", "el readme", "la documentación"]:
            readme = self.project_context.get("has_readme")
            if readme:
                return (Path.cwd() / readme).resolve()

        # Handle specific Spanish references like "el archivo html"
        if file_reference.lower() == "el archivo html":
            # Use the same logic as general HTML references
            file_index = self.project_context.get("file_index", {})
            if ".html" in file_index:
                html_files = file_index[".html"]
                if html_files:
                    # Prefer files in root directory
                    root_html_files = [f for f in html_files if f.parent == Path.cwd()]
                    if root_html_files:
                        return root_html_files[0]
                    return html_files[0]

        # HTML file references
        if "html" in file_reference.lower() and ".html" in file_index:
            html_files = file_index[".html"]
            if html_files:
                # If user specifies a specific file like "index.html", find it
                if "." in file_reference:
                    for html_file in html_files:
                        if html_file.name.lower() == file_reference.lower():
                            return html_file

                # For general "html" references, return the first/main one
                # Prefer files in root directory over subdirectories
                root_html_files = [f for f in html_files if f.parent == Path.cwd()]
                if root_html_files:
                    return root_html_files[0]
                return html_files[0]

        # Python file references
        if ("python" in file_reference.lower() or "py" in file_reference.lower()) and ".py" in file_index:
            py_files = file_index[".py"]
            # Filter out __pycache__ and similar
            main_py_files = [f for f in py_files if not f.name.startswith("__")]
            if main_py_files:
                # Look for main.py, app.py, etc.
                priority_names = ["main.py", "app.py", "server.py", "index.py"]
                for priority_name in priority_names:
                    for py_file in main_py_files:
                        if py_file.name == priority_name:
                            return py_file
                # Return the first non-special file
                return main_py_files[0]

        # Package.json references
        if ("package" in file_reference.lower() or "npm" in file_reference.lower()) and self.project_context.get("has_package_json"):
            return (Path.cwd() / "package.json").resolve()

        # Requirements.txt references
        if ("requirements" in file_reference.lower() or "pip" in file_reference.lower()) and self.project_context.get("has_requirements"):
            req_file = self.project_context["has_requirements"]
            return (Path.cwd() / req_file).resolve()

        return None

    def execute(
        self,
        file_path: str,
        start_line: int = 1,
        end_line: int = -1,
    ) -> Dict[str, Any]:
        """Read file contents with intelligent path resolution.

        Args:
            file_path: Path to file (can be reference like "index.html", "readme")
            start_line: Starting line (1-indexed)
            end_line: Ending line (-1 for all)

        Returns:
            Dictionary with file contents or error
        """
        try:
            # Resolve intelligent file reference (Zed-like)
            resolved_path = self._resolve_file_reference(file_path)

            # Check if file exists
            if not resolved_path.exists():
                # Provide helpful suggestions
                suggestions = []
                if self.project_context:
                    if "html" in file_path.lower() and ".html" in self.project_context.get("file_index", {}):
                        html_files = [f.name for f in self.project_context["file_index"][".html"]]
                        suggestions.append(f"Try one of these HTML files: {', '.join(html_files)}")
                    if "readme" in file_path.lower() and self.project_context.get("has_readme"):
                        suggestions.append(f"Try: {self.project_context['has_readme']}")

                error_msg = f"File not found: {file_path}"
                if resolved_path != Path(file_path):
                    error_msg += f" (resolved to: {resolved_path})"
                if suggestions:
                    error_msg += f"\nSuggestions: {'; '.join(suggestions)}"

                return {
                    "success": False,
                    "error": error_msg
                }

            if not resolved_path.is_file():
                return {
                    "success": False,
                    "error": f"Not a file: {resolved_path}"
                }

            # Read file contents
            with open(resolved_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            # Extract requested lines
            total_lines = len(lines)
            start_line = max(1, min(start_line, total_lines))
            if end_line == -1:
                end_line = total_lines
            else:
                end_line = max(start_line, min(end_line, total_lines))

            # Convert to 0-indexed
            selected_lines = lines[start_line - 1 : end_line]
            content = "".join(selected_lines)

            # Generate summary for ephemeral display
            lines_read = end_line - start_line + 1
            file_name = resolved_path.name
            summary = f"read {lines_read} lines from {file_name}"
            if lines_read != total_lines:
                summary += f" (lines {start_line}-{end_line} of {total_lines})"

            return {
                "success": True,
                "content": content,
                "file_path": str(resolved_path),
                "start_line": start_line,
                "end_line": end_line,
                "total_lines": total_lines,
                "summary": summary,
            }

        except UnicodeDecodeError:
            return {
                "success": False,
                "error": f"File appears to be binary or has encoding issues: {file_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}"
            }


class WriteFileTool(Tool):
    """Tool for writing content to a file."""

    def _get_name(self) -> str:
        return "write_file"

    def _get_description(self) -> str:
        return "✏️ WRITE/CREATE FILES: Use this to create brand new files or completely replace the contents of existing files. Ideal for writing code, configs, or any text content."

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    def execute(self, file_path: str, content: str) -> Dict[str, Any]:
        """Write content to file.

        Args:
            file_path: Path to file
            content: Content to write

        Returns:
            Dictionary with success status or error
        """
        try:
            # Validate path
            path = Path(file_path).expanduser().resolve()

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            # Generate summary
            bytes_written = len(content.encode("utf-8"))
            lines_written = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
            file_name = path.name
            summary = f"wrote {lines_written} lines ({bytes_written} bytes) to {file_name}"

            return {
                "success": True,
                "result": {
                    "message": f"Successfully wrote to {path}",
                    "file_path": str(path),
                    "bytes_written": bytes_written,
                },
                "summary": summary,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write file: {str(e)}"
            }


class EditFileTool(Tool):
    """Tool for editing file contents by replacing text."""

    def _get_name(self) -> str:
        return "edit_file"

    def _get_description(self) -> str:
        return "🔧 EDIT EXISTING FILES: Use this to make precise changes to existing files by replacing specific text. Perfect for fixing bugs, updating configs, or modifying code."

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit",
                },
                "old_text": {
                    "type": "string",
                    "description": "Text to search for and replace",
                },
                "new_text": {
                    "type": "string",
                    "description": "Text to replace with",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences (default: false, replaces first only)",
                    "default": False,
                },
            },
            "required": ["file_path", "old_text", "new_text"],
        }

    def execute(
        self,
        file_path: str,
        old_text: str,
        new_text: str,
        replace_all: bool = False,
    ) -> Dict[str, Any]:
        """Edit file by replacing text.

        Args:
            file_path: Path to file
            old_text: Text to replace
            new_text: Replacement text
            replace_all: Replace all occurrences

        Returns:
            Dictionary with success status or error
        """
        try:
            # Validate path
            path = Path(file_path).expanduser().resolve()

            if not path.exists():
                return {"error": f"File not found: {file_path}"}

            if not path.is_file():
                return {"error": f"Not a file: {file_path}"}

            # Read current content
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if old_text exists
            if old_text not in content:
                return {
                    "success": False,
                    "error": f"Text not found in file: {old_text[:50]}...",
                    "file_path": str(path),
                }

            # Replace text
            if replace_all:
                new_content = content.replace(old_text, new_text)
                count = content.count(old_text)
            else:
                new_content = content.replace(old_text, new_text, 1)
                count = 1

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # Generate summary
            file_name = path.name
            if count == 1:
                summary = f"edited {file_name} (1 replacement)"
            else:
                summary = f"edited {file_name} ({count} replacements)"

            return {
                "success": True,
                "result": {
                    "message": f"Successfully edited {path}",
                    "file_path": str(path),
                    "replacements": count,
                    "replace_all": replace_all,
                },
                "summary": summary,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to edit file: {str(e)}"
            }
