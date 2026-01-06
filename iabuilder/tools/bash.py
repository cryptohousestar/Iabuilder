"""Bash execution tool for running shell commands."""
import subprocess
import shlex
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .base import Tool


def clear_lines(num_lines: int):
    """Clear previous lines in terminal."""
    for _ in range(num_lines):
        sys.stdout.write('\033[A')  # Move up
        sys.stdout.write('\033[K')  # Clear line
    sys.stdout.flush()


class BashTool(Tool):
    """Tool for executing bash commands."""

    def __init__(self, safe_mode: bool = False):
        """Initialize bash tool.

        Args:
            safe_mode: If True, requires confirmation for destructive commands
        """
        self.safe_mode = safe_mode
        super().__init__()

    def _get_name(self) -> str:
        return "execute_bash"

    def _get_description(self) -> str:
        return "💻 RUN SYSTEM COMMANDS: Use this to execute any shell command, script, or system operation. Perfect for installing packages, running builds, starting servers, or any system task."

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory for command execution (default: current directory)",
                    "default": ".",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30)",
                    "default": 30,
                },
            },
            "required": ["command"],
        }

    def _is_potentially_destructive(self, command: str) -> bool:
        """Check if command is potentially destructive.

        Args:
            command: Command to check

        Returns:
            True if command might be destructive
        """
        destructive_patterns = [
            "rm ",
            "rmdir ",
            "del ",
            "format ",
            "mkfs",
            "> /dev/",
            "dd if=",
            "chmod -R",
            "chown -R",
        ]

        command_lower = command.lower()
        return any(pattern in command_lower for pattern in destructive_patterns)

    def execute(
        self,
        command: str,
        working_dir: str = ".",
        timeout: int = 30,
        stream_output: bool = True,
    ) -> Dict[str, Any]:
        """Execute bash command with optional streaming output.

        Args:
            command: Command to execute
            working_dir: Working directory
            timeout: Timeout in seconds
            stream_output: If True, show output in real-time then clear it

        Returns:
            Dictionary with command output and status
        """
        try:
            # Validate working directory
            work_path = Path(working_dir).expanduser().resolve()
            if not work_path.exists():
                return {"success": False, "error": f"Working directory not found: {working_dir}"}

            if not work_path.is_dir():
                return {"success": False, "error": f"Not a directory: {working_dir}"}

            # Safety check in safe mode
            if self.safe_mode and self._is_potentially_destructive(command):
                return {
                    "success": False,
                    "error": "Command blocked by safe mode",
                    "command": command,
                    "message": "This command appears to be potentially destructive. Disable safe mode to execute.",
                }

            if stream_output:
                return self._execute_with_streaming(command, work_path, timeout)
            else:
                return self._execute_silent(command, work_path, timeout)

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute command: {str(e)}",
                "command": command,
            }

    def _execute_silent(self, command: str, work_path: Path, timeout: int) -> Dict[str, Any]:
        """Execute command without streaming (original behavior)."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(work_path),
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            stdout_lines = result.stdout.strip().split('\n') if result.stdout else []
            stderr_lines = result.stderr.strip().split('\n') if result.stderr else []

            summary = self._generate_summary(command, result.returncode, stdout_lines, stderr_lines)

            result_dict = {
                "success": result.returncode == 0,
                "result": {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                    "command": command,
                    "working_dir": str(work_path),
                },
                "summary": summary
            }

            # Add error field if command failed
            if result.returncode != 0:
                result_dict["error"] = summary

            return result_dict
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "command": command,
                "timeout": timeout,
            }

    def _execute_with_streaming(self, command: str, work_path: Path, timeout: int) -> Dict[str, Any]:
        """Execute command with streaming output to terminal."""
        lines_printed = 0
        stdout_lines = []
        stderr_lines = []

        # Short command display
        cmd_display = command[:50] + "..." if len(command) > 50 else command

        try:
            # Print terminal box header
            print(f"\n\033[90m┌─ Terminal ─────────────────────────────────────────\033[0m")
            print(f"\033[90m│\033[0m \033[1;33m$\033[0m {cmd_display}")
            lines_printed = 2

            process = subprocess.Popen(
                command,
                shell=True,
                cwd=str(work_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # Read output in threads
            def read_stdout():
                for line in iter(process.stdout.readline, ''):
                    if line:
                        stdout_lines.append(line.rstrip())

            def read_stderr():
                for line in iter(process.stderr.readline, ''):
                    if line:
                        stderr_lines.append(line.rstrip())

            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            stdout_thread.start()
            stderr_thread.start()

            # Show output in real-time
            last_line_count = 0
            start_time = time.time()
            max_visible_lines = 8  # Show last N lines

            while process.poll() is None:
                current_lines = stdout_lines + stderr_lines
                if len(current_lines) > last_line_count:
                    # Clear previous output lines
                    for _ in range(min(last_line_count, max_visible_lines)):
                        sys.stdout.write('\033[A\033[K')

                    # Print last N lines
                    visible_lines = current_lines[-max_visible_lines:]
                    for line in visible_lines:
                        truncated = line[:60] + "..." if len(line) > 60 else line
                        print(f"\033[90m│\033[0m {truncated}")

                    last_line_count = len(visible_lines)
                    lines_printed = 2 + last_line_count

                # Check timeout
                if time.time() - start_time > timeout:
                    process.kill()
                    raise subprocess.TimeoutExpired(command, timeout)

                time.sleep(0.1)

            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)

            # Print footer
            exit_code = process.returncode
            status_icon = "✓" if exit_code == 0 else "✗"
            status_color = "\033[32m" if exit_code == 0 else "\033[31m"
            print(f"\033[90m└─ {status_color}{status_icon} Exit: {exit_code}\033[0m")
            lines_printed += 1

            # Build result
            full_stdout = '\n'.join(stdout_lines)
            full_stderr = '\n'.join(stderr_lines)

            # Only clear terminal box on SUCCESS
            # On error, keep output visible so user/model can see the error
            if exit_code == 0:
                time.sleep(0.3)
                clear_lines(lines_printed)
            else:
                # On error, show separator and keep output visible
                print(f"\033[90m{'─' * 55}\033[0m")
                time.sleep(0.5)  # Give more time to see error

            # Build summary
            summary = self._generate_summary(command, exit_code, stdout_lines, stderr_lines)

            result_dict = {
                "success": exit_code == 0,
                "result": {
                    "stdout": full_stdout,
                    "stderr": full_stderr,
                    "exit_code": exit_code,
                    "command": command,
                    "working_dir": str(work_path),
                },
                "summary": summary
            }

            # Add error field if command failed (so model can see the error)
            if exit_code != 0:
                result_dict["error"] = summary

            return result_dict

        except subprocess.TimeoutExpired:
            clear_lines(lines_printed)
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "command": command,
                "timeout": timeout,
            }

        except Exception as e:
            clear_lines(lines_printed)
            return {
                "success": False,
                "error": f"Streaming execution failed: {str(e)}",
                "command": command,
            }

    def _generate_summary(self, command: str, exit_code: int, stdout: list, stderr: list) -> str:
        """Generate a brief summary of command execution."""
        cmd_short = command.split()[0] if command else "command"

        # Detect common patterns
        output = '\n'.join(stdout + stderr).lower()

        if "npm" in cmd_short or "yarn" in cmd_short:
            if "added" in output:
                # Extract package count
                for line in stdout + stderr:
                    if "added" in line.lower() and "package" in line.lower():
                        return line.strip()
            if "up to date" in output:
                return "packages up to date"

        if exit_code == 0:
            return f"completed ({len(stdout)} lines output)"
        else:
            # Get error lines - show more context for the model
            err_lines = [l for l in stderr if l.strip()]
            if err_lines:
                # Show last 3 error lines, up to 200 chars total
                last_errors = err_lines[-3:]
                error_text = ' | '.join(last_errors)[:200]
                return f"FAILED (exit {exit_code}): {error_text}"
            # Check stdout for error messages too
            out_lines = [l for l in stdout if 'error' in l.lower() or 'failed' in l.lower()]
            if out_lines:
                return f"FAILED (exit {exit_code}): {out_lines[-1][:150]}"
            return f"FAILED with exit code {exit_code}"
