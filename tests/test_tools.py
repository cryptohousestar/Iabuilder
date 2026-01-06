#!/usr/bin/env python3
"""Test script for Groq CLI custom tools."""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)


def print_header(message):
    """Print a formatted header message."""
    print("\n" + "=" * 60)
    print(f" {message} ".center(60))
    print("=" * 60)


def print_success(message):
    """Print a success message."""
    print(f"✅ {message}")


def print_error(message):
    """Print an error message."""
    print(f"❌ {message}")


def test_file_tools():
    """Test the file operation tools."""
    print_header("Testing File Tools")

    try:
        # Import tools
        from iabuilder.tools.file_ops import EditFileTool, ReadFileTool, WriteFileTool

        # Create test file
        test_file = Path(script_dir) / "test_file.txt"

        # Test write_file
        write_tool = WriteFileTool()
        write_result = write_tool.execute(
            path=str(test_file), content="This is a test file.\nLine 2\nLine 3\n"
        )

        if write_result.get("success", False):
            print_success("WriteFileTool passed")
        else:
            print_error(f"WriteFileTool failed: {write_result.get('error')}")

        # Test read_file
        read_tool = ReadFileTool()
        read_result = read_tool.execute(path=str(test_file))

        if read_result.get("success", False):
            print_success("ReadFileTool passed")
        else:
            print_error(f"ReadFileTool failed: {read_result.get('error')}")

        # Test edit_file
        edit_tool = EditFileTool()
        edit_result = edit_tool.execute(
            path=str(test_file), search="Line 2", replace="Modified Line 2"
        )

        if edit_result.get("success", False):
            print_success("EditFileTool passed")
        else:
            print_error(f"EditFileTool failed: {edit_result.get('error')}")

        # Verify edit
        read_after_edit = read_tool.execute(path=str(test_file))
        if "Modified Line 2" in read_after_edit.get("result", {}).get("content", ""):
            print_success("Edit verification passed")
        else:
            print_error("Edit verification failed")

        # Clean up
        if test_file.exists():
            test_file.unlink()

    except Exception as e:
        print_error(f"Exception in file tools test: {e}")


def test_bash_tool():
    """Test the bash execution tool."""
    print_header("Testing Bash Tool")

    try:
        from iabuilder.tools.bash import BashTool

        bash_tool = BashTool()

        # Simple command
        ls_result = bash_tool.execute(command="ls -la", working_dir=script_dir)

        if ls_result.get("success", False):
            print_success("BashTool (ls) passed")
        else:
            print_error(f"BashTool (ls) failed: {ls_result.get('error')}")

        # Echo command
        echo_result = bash_tool.execute(
            command="echo 'Testing bash execution'", working_dir=script_dir
        )

        if echo_result.get("success", False):
            print_success("BashTool (echo) passed")
        else:
            print_error(f"BashTool (echo) failed: {echo_result.get('error')}")

    except Exception as e:
        print_error(f"Exception in bash tool test: {e}")


def test_background_tools():
    """Test background process tools."""
    print_header("Testing Background Process Tools")

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
            command="echo 'Test process started' && sleep 5 && echo 'Test process finished'",
            name="test_process",
            working_dir=script_dir,
        )

        if start_result.get("success", False):
            process_id = start_result.get("result", {}).get("process_id")
            print_success(
                f"StartBackgroundProcessTool passed (process_id: {process_id})"
            )
        else:
            print_error(
                f"StartBackgroundProcessTool failed: {start_result.get('error')}"
            )
            return

        # List processes
        list_tool = ListBackgroundProcessesTool()
        list_result = list_tool.execute()

        if list_result.get("success", False):
            processes = list_result.get("result", {}).get("processes", [])
            if len(processes) > 0:
                print_success(
                    f"ListBackgroundProcessesTool passed (found {len(processes)} processes)"
                )
            else:
                print_error("ListBackgroundProcessesTool failed: No processes found")
        else:
            print_error(
                f"ListBackgroundProcessesTool failed: {list_result.get('error')}"
            )

        # Get process status
        status_tool = GetBackgroundProcessStatusTool()
        status_result = status_tool.execute(process_id="test_process")

        if status_result.get("success", False):
            status = status_result.get("result", {}).get("status", {})
            is_running = status.get("is_running", False)
            print_success(
                f"GetBackgroundProcessStatusTool passed (running: {is_running})"
            )
        else:
            print_error(
                f"GetBackgroundProcessStatusTool failed: {status_result.get('error')}"
            )

        # Wait a bit for logs
        time.sleep(1)

        # Get process logs
        logs_tool = GetBackgroundProcessLogsTool()
        logs_result = logs_tool.execute(process_id="test_process")

        if logs_result.get("success", False):
            logs = logs_result.get("result", {}).get("logs", "")
            if "Test process started" in logs:
                print_success("GetBackgroundProcessLogsTool passed")
            else:
                print_error(
                    "GetBackgroundProcessLogsTool failed: Expected log message not found"
                )
        else:
            print_error(
                f"GetBackgroundProcessLogsTool failed: {logs_result.get('error')}"
            )

        # Wait for process to finish naturally (or stop it)
        stop_tool = StopBackgroundProcessTool()
        stop_result = stop_tool.execute(process_id="test_process")

        if stop_result.get("success", False):
            print_success("StopBackgroundProcessTool passed")
        else:
            print_error(f"StopBackgroundProcessTool failed: {stop_result.get('error')}")

    except Exception as e:
        print_error(f"Exception in background tools test: {e}")


def main():
    """Run all tests."""
    print_header("GROQ CLI TOOLS TEST")

    print("Testing basic tool functionality...")
    print("Current directory:", os.getcwd())

    # Run tests
    test_file_tools()
    test_bash_tool()
    test_background_tools()

    print_header("TESTS COMPLETED")


if __name__ == "__main__":
    main()
