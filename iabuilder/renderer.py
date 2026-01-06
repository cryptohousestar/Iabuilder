"""Markdown and response rendering with rich."""

import re
import time

from rich.box import ROUNDED
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table


class Renderer:
    """Handles rendering of responses and UI elements."""

    def __init__(self):
        """Initialize renderer."""
        self.console = Console()
        self.spinner = None
        self.progress = None
        self._status = None  # For animated spinner
        self._spinner_active = False
        self.theme = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "tool": "blue",
            "assistant": "green",
            "user": "blue",
            "system": "magenta",
            "prompt": "cyan bold",
        }
        self.box_style = ROUNDED

    def render_markdown(self, text: str):
        """Render markdown text with improved code block handling.

        Args:
            text: Markdown text to render
        """
        # Clear any remaining output on the current line first
        print("\033[2K", end="\r")
        # Check if we need to process code blocks
        if "```" in text:
            # Process code blocks with syntax highlighting
            processed_text = self._process_code_blocks(text)
            self.console.print(processed_text)
        else:
            try:
                md = Markdown(text)
                self.console.print(md)
            except Exception:
                # Fallback if markdown parsing fails
                self.console.print(text)

    def _process_code_blocks(self, text: str):
        """Process code blocks in markdown text.

        Args:
            text: Text containing markdown code blocks

        Returns:
            Rich renderable object
        """
        # Split by code blocks
        parts = re.split(r"(```(?:[\w+#\-\.]*)\n[\s\S]*?\n```)", text)

        from rich.console import Group

        elements = []

        for part in parts:
            if part.startswith("```") and part.endswith("```"):
                # Extract language and code
                first_line_end = part.find("\n")
                lang_spec = part[3:first_line_end].strip()
                code = part[first_line_end + 1 : -4].rstrip()

                # Determine language
                lang = None
                if lang_spec and not lang_spec.startswith("/"):
                    lang = lang_spec

                # Create syntax highlighted code block
                syntax = Syntax(
                    code,
                    lang or "text",
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True,
                    background_color="default",
                )
                elements.append(Panel(syntax, border_style="dim"))
            else:
                if part.strip():
                    elements.append(Markdown(part))

        return Group(*elements)

    def render_assistant_message(self, content: str):
        """Render assistant message with visual styling.

        Args:
            content: Message content (markdown)
        """
        # Stop typing animation if active
        self._stop_spinner()

        # Simple print output
        print(f"\n{content}\n")

    def _start_spinner(self, message="Thinking..."):
        """Start an animated spinner to indicate processing.

        Args:
            message: Message to display next to spinner
        """
        if self._spinner_active:
            return

        try:
            from rich.status import Status
            self._status = Status(
                f"[cyan]{message}[/cyan]",
                spinner="dots",
                spinner_style="cyan"
            )
            self._status.start()
            self._spinner_active = True
        except Exception:
            # Fallback to simple print
            print(f"\n{message}", end="", flush=True)

    def _stop_spinner(self):
        """Stop the spinner if it's running."""
        if self._status and self._spinner_active:
            try:
                self._status.stop()
                self._spinner_active = False
                self._status = None
            except Exception:
                pass
        # Don't print anything - the spinner cleanup is silent

    def render_error(self, message: str):
        """Render error message with visual styling.

        Args:
            message: Error message
        """
        self.console.print(
            Panel(
                f"{message}",
                border_style=self.theme["error"],
                box=self.box_style,
                title="[bold red]Error[/bold red]",
                padding=(1, 2),
            )
        )

    def render_warning(self, message: str):
        """Render warning message with visual styling.

        Args:
            message: Warning message
        """
        self.console.print(
            Panel(
                f"{message}",
                border_style=self.theme["warning"],
                box=self.box_style,
                title="[bold yellow]Warning[/bold yellow]",
                padding=(1, 1),
            )
        )

    def render_info(self, message: str):
        """Render info message with visual styling.

        Args:
            message: Info message
        """
        self.console.print(f"[{self.theme['info']}]ℹ[/{self.theme['info']}] {message}")

    def render_success(self, message: str):
        """Render success message with visual styling.

        Args:
            message: Success message
        """
        self.console.print(
            f"[bold {self.theme['success']}]✓[/bold {self.theme['success']}] {message}"
        )

    def render_tool_call(self, tool_name: str, arguments: str):
        """Render tool call notification with visual styling.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments (JSON string)
        """
        # Start a spinner to indicate processing
        self._start_spinner(f"Running tool: {tool_name}")

        self.console.print(
            Panel(
                f"[bold]{tool_name}[/bold]\n{arguments}",
                border_style=self.theme["tool"],
                box=self.box_style,
                title="[bold]🔧 Tool Call[/bold]",
                title_align="left",
                padding=(1, 1),
                width=min(100, self.console.width - 10),
            )
        )

    def render_tool_result(self, result: dict):
        """Render tool execution result with visual styling.

        Args:
            result: Tool result dictionary
        """
        self._stop_spinner()

        if result.get("success", True):
            self.console.print(
                Panel(
                    str(result.get("result", "Operation completed")),
                    border_style="green dim",
                    box=self.box_style,
                    title="[bold green]✓ Tool Result[/bold green]",
                    title_align="left",
                    padding=(1, 1),
                    width=min(100, self.console.width - 10),
                )
            )
        else:
            error = result.get("error", "Unknown error")
            self.console.print(
                Panel(
                    f"[red]{error}[/red]",
                    border_style="red dim",
                    box=self.box_style,
                    title="[bold red]✗ Tool Failed[/bold red]",
                    title_align="left",
                    padding=(1, 1),
                    width=min(100, self.console.width - 10),
                )
            )

    def render_welcome(self):
        """Render welcome message with improved styling."""
        welcome_text = """
# Welcome to Groq Custom CLI 🚀

An interactive terminal-based AI assistant with coding tools and file operations.

**Commands:**
- `/help` - Show help and available commands
- `/model` - List or switch models
- `/clear` - Clear conversation history
- `/history` - Show conversation history
- `/save [filename]` - Export conversation to markdown
- `/tools` - List available tools
- `/compress` - Manually compress conversation context
- `/stats` - Show conversation and token statistics
- `/resume [id]` - View or resume compressed sessions
- `/exit` or `/quit` - Exit the application

## Current Working Directory:
"""
        # Add working directory information
        import os

        welcome_text += f"`{os.getcwd()}`\n\n"

        # Add tools information
        welcome_text += "## Available Tools:\n"
        welcome_text += "- 📂 **File**: read_file, write_file, edit_file\n"
        welcome_text += "- 🖥️ **System**: execute_bash (terminal commands)\n"
        welcome_text += "- 🌐 **Web**: web_search (DuckDuckGo)\n\n"
        welcome_text += "Start typing to chat!"

        layout = Layout()
        layout.split_column(
            Layout(name="header"), Layout(name="body"), Layout(name="footer")
        )

        # Header with logo
        logo = """
  _____                    _____           _
 / ____|                  / ____|         | |
| |  __ _ __ ___   __ _  | |    _   _ ___| |_ ___  _ __ ___
| | |_ | '__/ _ \\ / _` | | |   | | | / __| __/ _ \\| '_ ` _ \\
| |__| | | | (_) | (_| | | |___| |_| \\__ \\ || (_) | | | | | |
 \\_____|_|  \\___/ \\__, |  \\_____\\__,_|___/\\__\\___/|_| |_| |_|
                    __/ |
                   |___/
"""

        header_panel = Panel(
            f"[bold blue]{logo}[/bold blue]",
            box=self.box_style,
            border_style="blue",
            padding=(1, 2),
        )
        layout["header"].update(header_panel)

        # Main content
        content_panel = Panel(
            Markdown(welcome_text),
            title="[bold cyan]Interactive AI Terminal[/bold cyan]",
            title_align="center",
            border_style="cyan",
            box=self.box_style,
            padding=(1, 2),
        )
        layout["body"].update(content_panel)

        # Footer
        import datetime

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        footer_text = f"[italic]Session started at {current_time} • Type `/help` for more information • Press Ctrl+D to exit[/italic]"
        footer_panel = Panel(
            footer_text, box=self.box_style, border_style="cyan dim", padding=(0, 1)
        )
        layout["footer"].update(footer_panel)

        # Render the full layout
        self.console.print(layout)
        self.console.print()

    def render_model_list(self, models: dict, current_model: str):
        """Render available models list with improved styling.

        Args:
            models: Dictionary of categorized models
            current_model: Currently selected model
        """
        table = Table(
            title="[bold]Available Groq Models[/bold]",
            box=self.box_style,
            header_style="bold cyan",
            border_style="blue",
            title_style="bold cyan",
            title_justify="center",
            padding=(0, 1),
        )

        table.add_column("Category", style="cyan bold", justify="center")
        table.add_column("Model ID", style="white")
        table.add_column("Status", style="green", justify="center", width=12)
        table.add_column("Provider", style="dim", width=15)

        # Process models by category
        for category, model_list in models.items():
            if not model_list:
                continue

            # Sort models alphabetically
            model_list = sorted(model_list)

            # Create rows for each model
            for model in model_list:
                is_current = model == current_model
                status = "[bold green]ACTIVE[/bold green]" if is_current else ""

                # Determine provider based on model name
                provider = ""
                if "meta" in model.lower() or "llama" in model.lower():
                    provider = "Meta"
                elif "groq" in model.lower():
                    provider = "Groq"
                elif "openai" in model.lower() or "gpt" in model.lower():
                    provider = "OpenAI"
                elif "qwen" in model.lower():
                    provider = "Alibaba"
                elif "moonshot" in model.lower() or "kimi" in model.lower():
                    provider = "Moonshot AI"

                # Style current model differently
                model_display = (
                    f"[bold cyan]{model}[/bold cyan]" if is_current else model
                )

                table.add_row(category.upper(), model_display, status, provider)

        self.console.print(
            Panel(
                table,
                border_style="blue",
                box=self.box_style,
                title="[bold blue]Model Selection[/bold blue]",
                title_align="left",
                padding=(1, 1),
            )
        )

    def render_tools_list(self, tools: list):
        """Render available tools list with improved styling and categories.

        Args:
            tools: List of tool names
        """
        # Tool descriptions and categories (5 essential tools)
        tool_info = {
            "read_file": {
                "desc": "Read contents of a file with optional line ranges",
                "category": "File Operations",
                "emoji": "📄",
                "example": 'read_file(path="/path/to/file.txt", start_line=10, end_line=20)',
            },
            "write_file": {
                "desc": "Write or create a file with specified content",
                "category": "File Operations",
                "emoji": "💾",
                "example": 'write_file(path="/path/to/file.txt", content="Hello world!")',
            },
            "edit_file": {
                "desc": "Edit an existing file (replace text or lines)",
                "category": "File Operations",
                "emoji": "✏️",
                "example": 'edit_file(path="/path/to/file.txt", changes=[{"from": "old", "to": "new"}])',
            },
            "execute_bash": {
                "desc": "Execute bash/shell commands (grep, find, curl, npm, pip, docker, etc.)",
                "category": "System",
                "emoji": "🖥️",
                "example": 'execute_bash(command="ls -la", working_dir="/path/to/dir")',
            },
            "web_search": {
                "desc": "Search the web using DuckDuckGo",
                "category": "Web",
                "emoji": "🌐",
                "example": 'web_search(query="python tutorial", max_results=5)',
            },
        }

        # Organize tools by category
        categories = {}
        for tool in tools:
            info = tool_info.get(
                tool,
                {
                    "desc": "No description available",
                    "category": "Other",
                    "emoji": "❓",
                    "example": f"{tool}()",
                },
            )

            category = info["category"]
            if category not in categories:
                categories[category] = []

            categories[category].append({"name": tool, "info": info})

        # Create the main table
        main_table = Table(
            title="[bold]Available AI Tools[/bold]",
            box=self.box_style,
            title_style="bold cyan",
            border_style="blue",
            header_style="bold cyan",
            padding=(0, 1),
        )

        main_table.add_column("Category", style="cyan bold")
        main_table.add_column("Tool", style="green")
        main_table.add_column("Description", style="white")
        main_table.add_column("Example Usage", style="dim italic", overflow="fold")

        # Add rows for each tool, grouped by category
        for category, category_tools in sorted(categories.items()):
            for i, tool_data in enumerate(
                sorted(category_tools, key=lambda x: x["name"])
            ):
                tool = tool_data["name"]
                info = tool_data["info"]

                # Only show category name on the first row of each category
                cat_display = f"[bold]{category}[/bold]" if i == 0 else ""

                main_table.add_row(
                    cat_display,
                    f"{info['emoji']} [bold]{tool}[/bold]",
                    info["desc"],
                    info["example"],
                )

        # Render with a panel
        self.console.print(
            Panel(
                main_table,
                border_style="blue",
                box=self.box_style,
                title="[bold blue]🧰 Tool Reference[/bold blue]",
                title_align="left",
                padding=(1, 1),
            )
        )

        # Add a note about automatic tool use
        self.console.print(
            "[italic cyan]Note: The AI will automatically use these tools when needed based on your requests.[/italic cyan]\n"
        )
        self.console.print(
            "[dim]Tip: Use execute_bash for grep, find, curl, npm, pip, docker, and other terminal commands.[/dim]\n"
        )

    def render_help(self):
        """Render help message with improved styling and comprehensive info."""
        # Create a layout
        layout = Layout()
        layout.split_column(
            Layout(name="header"),
            Layout(name="commands"),
            Layout(name="tools"),
            Layout(name="tips"),
        )

        # Header
        layout["header"].update(
            Panel(
                "[bold cyan]Groq Custom CLI[/bold cyan] - An AI assistant with tools for developers",
                box=self.box_style,
                border_style="blue",
                padding=(1, 1),
            )
        )

        # Commands section
        commands_table = Table(
            box=self.box_style,
            title="[bold]Available Commands[/bold]",
            title_style="bold blue",
            border_style="blue",
            padding=(0, 1),
        )

        commands_table.add_column("Command", style="cyan bold")
        commands_table.add_column("Description", style="white")
        commands_table.add_column("Example", style="dim")

        commands = [
            ("/help", "Show this help message", "/help"),
            ("/model", "List all available models", "/model"),
            (
                "/model <name>",
                "Switch to a specific model",
                "/model llama-3.1-8b-instant",
            ),
            ("/model --category", "List models by category", "/model --llm"),
            ("/clear", "Clear the current conversation", "/clear"),
            ("/history", "Show conversation history", "/history"),
            ("/save", "Save conversation to markdown file", "/save my_chat.md"),
            ("/tools", "List available AI tools", "/tools"),
            ("/compress", "Manually compress conversation context", "/compress"),
            ("/stats", "View token usage and compression stats", "/stats"),
            ("/resume", "List compressed conversation sessions", "/resume"),
            (
                "/resume <id>",
                "View details of a compressed session",
                "/resume 20231225_120159",
            ),
            ("/exit or /quit", "Exit the application", "/exit"),
        ]

        for cmd, desc, example in commands:
            commands_table.add_row(cmd, desc, example)

        layout["commands"].update(
            Panel(
                commands_table,
                box=self.box_style,
                border_style="blue",
                title="[bold blue]📋 Commands[/bold blue]",
                padding=(1, 1),
            )
        )

        # Tools section - 5 essential tools
        tools_text = """
## File Operations
- 📄 **read_file** - Read file contents with line ranges
- 💾 **write_file** - Create or write to files
- ✏️  **edit_file** - Edit existing files (replace content)

## System Operations
- 🖥️  **execute_bash** - Run any shell command (grep, find, npm, pip, docker, git, etc.)

## Web
- 🌐 **web_search** - Search the internet with DuckDuckGo

Use `/tools` for detailed information and examples.
"""
        layout["tools"].update(
            Panel(
                Markdown(tools_text),
                box=self.box_style,
                border_style="blue",
                title="[bold blue]🧰 Available Tools[/bold blue]",
                padding=(1, 1),
            )
        )

        # Tips section
        tips_text = """
### Keyboard Shortcuts
- `Alt+Enter` - Insert newline (for multiline input)
- `Ctrl+C` - Cancel current input
- `Ctrl+D` - Exit application
- `Up/Down` - Navigate through command history

### Best Practices
- Start with clear, specific questions
- For file operations, provide specific paths
- When asking for code, specify language and requirements
- Use `/compress` before long sessions to save context
- Use `/model llama-3.1-8b-instant` for faster responses
- Use `/model llama-3.3-70b-versatile` for complex tasks

### Working Directory
All file operations are relative to your current working directory.
"""
        layout["tips"].update(
            Panel(
                Markdown(tips_text),
                box=self.box_style,
                border_style="blue",
                title="[bold blue]💡 Tips & Shortcuts[/bold blue]",
                padding=(1, 1),
            )
        )

        # Render the whole layout
        self.console.print(layout)
        self.console.print()

    def clear_screen(self):
        """Clear the terminal screen."""
        self.console.clear()

    def show_thinking(self):
        """Show an animated thinking spinner while waiting for a response."""
        self._start_spinner("🤔 Thinking...")

    def show_waiting(self, seconds: int = 0):
        """Show waiting animation for rate limit delays.

        Args:
            seconds: Estimated wait time in seconds
        """
        if seconds > 0:
            self._start_spinner(f"⏳ Waiting for API... ({seconds}s)")
        else:
            self._start_spinner("⏳ Waiting for API...")

    def update_spinner_message(self, message: str):
        """Update the spinner message without stopping it.

        Args:
            message: New message to display
        """
        if self._status and self._spinner_active:
            try:
                self._status.update(f"[cyan]{message}[/cyan]")
            except Exception:
                pass

    def simulate_typing(self, text, speed=0.01):
        """Simulate typing effect for text.

        Args:
            text: Text to display with typing effect
            speed: Delay between characters in seconds
        """
        with Live("", console=self.console, refresh_per_second=20) as live:
            typed_text = ""
            for char in text:
                typed_text += char
                live.update(typed_text)
                time.sleep(speed)


# Global renderer instance
_renderer = None


def get_renderer() -> Renderer:
    """Get or create global renderer instance.

    Returns:
        Renderer instance
    """
    global _renderer
    if _renderer is None:
        _renderer = Renderer()
    return _renderer
