#!/usr/bin/env python3
"""
Complete test script for IABuilder.
This script tests all the main functionality of the IABuilder application.
"""

import os
import sys
import time
import unittest
from pathlib import Path

# Get the absolute path to the project root directory
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)


class TestIABuilder(unittest.TestCase):
    """Test case for IABuilder."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(script_dir) / "test_files"
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        # Remove test files
        for file_path in self.test_dir.glob("*"):
            try:
                if file_path.is_file():
                    file_path.unlink()
            except Exception as e:
                print(f"Warning: Failed to delete {file_path}: {e}")

    def test_imports(self):
        """Test that all required modules can be imported."""
        print("Testing imports...")

        try:
            # Core modules
            from iabuilder.cli import CLI
            from iabuilder.client import GroqClient
            from iabuilder.conversation import Conversation
            from iabuilder.main import IABuilderApp
            from iabuilder.renderer import Renderer

            # Tools
            from iabuilder.tools import (
                Tool,
                get_tool_registry,
                register_tool,
            )
            from iabuilder.tools.background_tools import (
                GetBackgroundProcessLogsTool,
                GetBackgroundProcessStatusTool,
                ListBackgroundProcessesTool,
                StartBackgroundProcessTool,
                StopBackgroundProcessTool,
            )
            from iabuilder.tools.bash import BashTool
            from iabuilder.tools.file_ops import (
                EditFileTool,
                ReadFileTool,
                WriteFileTool,
            )

            # Ensure the process manager exists
            from iabuilder.tools.process_manager import (
                BackgroundProcess,
                ProcessManager,
                get_process_manager,
            )
            from iabuilder.tools.search import GlobSearchTool, GrepSearchTool
            from iabuilder.tools.web import WebSearchTool

            print("✅ All modules imported successfully")
        except ImportError as e:
            self.fail(f"Import error: {e}")

    def test_file_tools(self):
        """Test the file operation tools."""
        print("Testing file tools...")

        try:
            # Import tools
            from iabuilder.tools.file_ops import (
                EditFileTool,
                ReadFileTool,
                WriteFileTool,
            )

            # Create test file path
            test_file = self.test_dir / "test_file.txt"

            # Test write_file
            write_tool = WriteFileTool()
            write_result = write_tool.execute(
                file_path=str(test_file), content="This is a test file.\nLine 2\nLine 3\n"
            )

            self.assertTrue(
                write_result.get("success", False),
                f"WriteFileTool failed: {write_result.get('error')}",
            )

            # Test read_file
            read_tool = ReadFileTool()
            read_result = read_tool.execute(file_path=str(test_file))

            self.assertTrue(
                read_result.get("success", False),
                f"ReadFileTool failed: {read_result.get('error')}",
            )

            # Test edit_file
            edit_tool = EditFileTool()
            edit_result = edit_tool.execute(
                file_path=str(test_file), old_text="Line 2", new_text="Modified Line 2"
            )

            self.assertTrue(
                edit_result.get("success", False),
                f"EditFileTool failed: {edit_result.get('error')}",
            )

            # Verify edit
            read_after_edit = read_tool.execute(file_path=str(test_file))
            self.assertIn(
                "Modified Line 2",
                read_after_edit.get("content", ""),
                "Edit verification failed",
            )

            print("✅ File tools tests passed")
        except Exception as e:
            self.fail(f"Exception in file tools test: {e}")

    def test_bash_tool(self):
        """Test the bash execution tool."""
        print("Testing bash tool...")

        try:
            from iabuilder.tools.bash import BashTool

            bash_tool = BashTool()

            # Test simple ls command
            ls_result = bash_tool.execute(command="ls -la", working_dir=script_dir)

            self.assertTrue(
                ls_result.get("success", False),
                f"BashTool (ls) failed: {ls_result.get('error')}",
            )

            # Test echo command
            echo_result = bash_tool.execute(
                command="echo 'Testing bash execution'", working_dir=script_dir
            )

            self.assertTrue(
                echo_result.get("success", False),
                f"BashTool (echo) failed: {echo_result.get('error')}",
            )

            print("✅ Bash tool tests passed")
        except Exception as e:
            self.fail(f"Exception in bash tool test: {e}")

    def test_background_tools(self):
        """Test background process tools."""
        print("Testing background process tools...")

        try:
            from iabuilder.tools.background_tools import (
                GetBackgroundProcessLogsTool,
                GetBackgroundProcessStatusTool,
                ListBackgroundProcessesTool,
                StartBackgroundProcessTool,
                StopBackgroundProcessTool,
            )

            # Start a simple background process
            start_tool = StartBackgroundProcessTool()
            start_result = start_tool.execute(
                command="echo 'Test process started' && sleep 2 && echo 'Test process finished'",
                name="test_process",
                working_dir=script_dir,
            )

            self.assertTrue(
                start_result.get("success", False),
                f"StartBackgroundProcessTool failed: {start_result.get('error')}",
            )

            process_id = start_result.get("result", {}).get("process_id")

            # List processes
            list_tool = ListBackgroundProcessesTool()
            list_result = list_tool.execute()

            self.assertTrue(
                list_result.get("success", False),
                f"ListBackgroundProcessesTool failed: {list_result.get('error')}",
            )

            processes = list_result.get("result", {}).get("processes", [])
            self.assertGreater(
                len(processes), 0, "No processes found after starting one"
            )

            # Get process status
            status_tool = GetBackgroundProcessStatusTool()
            status_result = status_tool.execute(process_id="test_process")

            self.assertTrue(
                status_result.get("success", False),
                f"GetBackgroundProcessStatusTool failed: {status_result.get('error')}",
            )

            # Wait a bit for logs
            time.sleep(0.5)

            # Get process logs
            logs_tool = GetBackgroundProcessLogsTool()
            logs_result = logs_tool.execute(process_id="test_process")

            self.assertTrue(
                logs_result.get("success", False),
                f"GetBackgroundProcessLogsTool failed: {logs_result.get('error')}",
            )

            # Wait for process to finish or stop it
            stop_tool = StopBackgroundProcessTool()
            stop_result = stop_tool.execute(process_id="test_process")

            print("✅ Background process tools tests passed")
        except Exception as e:
            self.fail(f"Exception in background tools test: {e}")

    def test_conversation(self):
        """Test the conversation module."""
        print("Testing conversation module...")

        try:
            from iabuilder.conversation import Conversation

            # Create a conversation
            conversation = Conversation(auto_save=False, enable_compression=False)

            # Add a user message
            conversation.add_message("user", "Test message")

            # Add an assistant message
            conversation.add_message("assistant", "Test response")

            # Get messages
            messages = conversation.get_messages()
            self.assertGreaterEqual(len(messages), 3)  # Including system message

            # Get messages for API
            api_messages = conversation.get_messages_for_api()
            self.assertGreaterEqual(len(api_messages), 3)  # Including system message

            print("✅ Conversation module tests passed")
        except Exception as e:
            self.fail(f"Exception in conversation test: {e}")

    def test_process_manager(self):
        """Test the process manager directly."""
        print("Testing process manager...")

        try:
            from iabuilder.tools.process_manager import get_process_manager

            # Get process manager
            manager = get_process_manager()

            # Start a process
            success, process_id, error = manager.start_process(
                command="echo 'Process manager test' && sleep 1",
                working_dir=script_dir,
                name="process_manager_test",
            )

            self.assertTrue(success, f"Failed to start process: {error}")

            # List processes
            processes = manager.list_processes()
            self.assertGreaterEqual(
                len(processes), 1, "No processes found after starting one"
            )

            # Get process status
            success, status = manager.get_process_status("process_manager_test")
            self.assertTrue(success, "Failed to get process status")

            # Wait for the process to complete or force cleanup
            time.sleep(2)
            manager.cleanup()

            print("✅ Process manager tests passed")
        except Exception as e:
            self.fail(f"Exception in process manager test: {e}")


def main():
    """Run the tests."""
    print("=" * 60)
    print("GROQ CLI CUSTOM COMPLETE TEST")
    print("=" * 60)
    print(f"Running tests in: {script_dir}")
    print("-" * 60)

    # Run tests
    unittest.main(argv=["first-arg-is-ignored"], exit=False)


if __name__ == "__main__":
    main()
