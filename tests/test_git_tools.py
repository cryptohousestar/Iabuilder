"""Tests for Git tools in Groq CLI Custom."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from iabuilder.tools.git_tools import (
    GitBranchTool,
    GitCommitTool,
    GitLogTool,
    GitRemoteTool,
    GitStatusTool,
)


class TestGitTools(unittest.TestCase):
    """Test cases for Git tools."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.test_dir) / "test_repo"
        self.repo_path.mkdir()

        # Initialize git repository
        subprocess.run(
            ["git", "init"],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )

        # Configure git user for testing
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )

        # Create a test file
        test_file = self.repo_path / "test.txt"
        test_file.write_text("Initial content")

        # Make initial commit
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_git_status_tool(self):
        """Test GitStatusTool functionality."""
        tool = GitStatusTool()

        # Test clean repository
        result = tool.execute(path=str(self.repo_path))
        self.assertTrue(result["success"])
        self.assertTrue(result["is_clean"])
        self.assertEqual(result["current_branch"], "master")  # or "main"

        # Create unstaged changes
        test_file = self.repo_path / "test.txt"
        test_file.write_text("Modified content")

        result = tool.execute(path=str(self.repo_path))
        self.assertTrue(result["success"])
        self.assertFalse(result["is_clean"])
        self.assertTrue(result["has_unstaged_changes"])

        # Test with diff
        result = tool.execute(path=str(self.repo_path), show_diff=True)
        self.assertTrue(result["success"])
        self.assertIn("diff", result)

        # Test non-git directory
        non_git_path = Path(self.test_dir) / "non_git"
        non_git_path.mkdir()
        result = tool.execute(path=str(non_git_path))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "NotGitRepository")

    def test_git_commit_tool(self):
        """Test GitCommitTool functionality."""
        tool = GitCommitTool()

        # Create changes to commit
        test_file = self.repo_path / "new_file.txt"
        test_file.write_text("New file content")

        # Test commit with custom message
        result = tool.execute(
            message="Add new file",
            path=str(self.repo_path),
            add_all=True,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Add new file")
        self.assertIn("commit_hash", result)

        # Create more changes for auto-message test
        another_file = self.repo_path / "another.txt"
        another_file.write_text("Another file")

        # Test commit with auto-generated message
        result = tool.execute(
            path=str(self.repo_path),
            add_all=True,
            auto_message=True,
        )
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["message"])

        # Test commit specific files
        specific_file = self.repo_path / "specific.txt"
        specific_file.write_text("Specific file")

        result = tool.execute(
            message="Add specific file",
            path=str(self.repo_path),
            files=["specific.txt"],
        )
        self.assertTrue(result["success"])

        # Test non-git directory
        non_git_path = Path(self.test_dir) / "non_git"
        non_git_path.mkdir()
        result = tool.execute(path=str(non_git_path))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "NotGitRepository")

    def test_git_branch_tool(self):
        """Test GitBranchTool functionality."""
        tool = GitBranchTool()

        # Test list branches
        result = tool.execute(action="list", path=str(self.repo_path))
        self.assertTrue(result["success"])
        self.assertIn("branches", result)
        self.assertIn("current_branch", result)

        # Test create branch
        result = tool.execute(
            action="create",
            branch_name="feature-test",
            path=str(self.repo_path),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["branch_name"], "feature-test")

        # Test switch branch
        result = tool.execute(
            action="switch",
            branch_name="master",  # or "main"
            path=str(self.repo_path),
        )
        # This might fail if the default branch is "main", so check both
        if not result["success"]:
            result = tool.execute(
                action="switch",
                branch_name="main",
                path=str(self.repo_path),
            )

        # Test delete branch
        result = tool.execute(
            action="delete",
            branch_name="feature-test",
            path=str(self.repo_path),
        )
        self.assertTrue(result["success"])

        # Test missing parameter
        result = tool.execute(action="create", path=str(self.repo_path))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingParameter")

        # Test invalid action
        result = tool.execute(action="invalid", path=str(self.repo_path))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "InvalidAction")

    def test_git_log_tool(self):
        """Test GitLogTool functionality."""
        tool = GitLogTool()

        # Make a few more commits for testing
        for i in range(3):
            test_file = self.repo_path / f"file_{i}.txt"
            test_file.write_text(f"Content {i}")
            subprocess.run(
                ["git", "add", f"file_{i}.txt"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i}"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )

        # Test basic log
        result = tool.execute(path=str(self.repo_path), limit=5)
        self.assertTrue(result["success"])
        self.assertIn("commits", result)
        self.assertLessEqual(len(result["commits"]), 5)

        # Test oneline format
        result = tool.execute(path=str(self.repo_path), oneline=True, limit=3)
        self.assertTrue(result["success"])
        self.assertIn("commits", result)
        for commit in result["commits"]:
            self.assertIn("oneline", commit)

        # Test with author filter (should work with our test user)
        result = tool.execute(
            path=str(self.repo_path),
            author="Test User",
            limit=5,
        )
        self.assertTrue(result["success"])

        # Test with file path
        result = tool.execute(
            path=str(self.repo_path),
            file_path="test.txt",
            limit=5,
        )
        self.assertTrue(result["success"])

        # Test non-git directory
        non_git_path = Path(self.test_dir) / "non_git"
        non_git_path.mkdir()
        result = tool.execute(path=str(non_git_path))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "NotGitRepository")

    def test_git_remote_tool(self):
        """Test GitRemoteTool functionality."""
        tool = GitRemoteTool()

        # Test list remotes (should be empty initially)
        result = tool.execute(action="list", path=str(self.repo_path))
        self.assertTrue(result["success"])
        self.assertIn("remotes", result)

        # Test add remote
        result = tool.execute(
            action="add",
            remote_name="origin",
            url="https://github.com/test/repo.git",
            path=str(self.repo_path),
        )
        self.assertTrue(result["success"])

        # Test list remotes after adding
        result = tool.execute(action="list", path=str(self.repo_path))
        self.assertTrue(result["success"])
        self.assertTrue(len(result["remotes"]) > 0)

        # Test remove remote
        result = tool.execute(
            action="remove",
            remote_name="origin",
            path=str(self.repo_path),
        )
        self.assertTrue(result["success"])

        # Test missing URL for add
        result = tool.execute(
            action="add",
            remote_name="test",
            path=str(self.repo_path),
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "MissingParameter")

        # Test invalid action
        result = tool.execute(action="invalid", path=str(self.repo_path))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "InvalidAction")

        # Test non-git directory
        non_git_path = Path(self.test_dir) / "non_git"
        non_git_path.mkdir()
        result = tool.execute(action="list", path=str(non_git_path))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "NotGitRepository")

    def test_tools_integration(self):
        """Test that all tools work together properly."""
        status_tool = GitStatusTool()
        commit_tool = GitCommitTool()
        branch_tool = GitBranchTool()

        # Check initial status
        status_result = status_tool.execute(path=str(self.repo_path))
        self.assertTrue(status_result["success"])
        initial_branch = status_result["current_branch"]

        # Create a new branch
        branch_result = branch_tool.execute(
            action="create",
            branch_name="integration-test",
            path=str(self.repo_path),
        )
        self.assertTrue(branch_result["success"])

        # Make changes and commit
        test_file = self.repo_path / "integration.txt"
        test_file.write_text("Integration test")

        commit_result = commit_tool.execute(
            message="Integration test commit",
            path=str(self.repo_path),
            add_all=True,
        )
        self.assertTrue(commit_result["success"])

        # Check status after commit
        status_result = status_tool.execute(path=str(self.repo_path))
        self.assertTrue(status_result["success"])
        self.assertTrue(status_result["is_clean"])
        self.assertEqual(status_result["current_branch"], "integration-test")

        # Switch back to original branch
        branch_result = branch_tool.execute(
            action="switch",
            branch_name=initial_branch,
            path=str(self.repo_path),
        )
        self.assertTrue(branch_result["success"])


class TestGitToolsWithoutRepo(unittest.TestCase):
    """Test Git tools behavior when no repository exists."""

    def setUp(self):
        """Set up test environment without git repository."""
        self.test_dir = tempfile.mkdtemp()
        self.non_repo_path = Path(self.test_dir) / "non_repo"
        self.non_repo_path.mkdir()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_all_tools_handle_non_repo(self):
        """Test that all Git tools gracefully handle non-repository directories."""
        tools = [
            GitStatusTool(),
            GitCommitTool(),
            GitBranchTool(),
            GitLogTool(),
            GitRemoteTool(),
        ]

        for tool in tools:
            # Test with minimal parameters for each tool
            if isinstance(tool, GitBranchTool):
                result = tool.execute(action="list", path=str(self.non_repo_path))
            elif isinstance(tool, GitRemoteTool):
                result = tool.execute(action="list", path=str(self.non_repo_path))
            else:
                result = tool.execute(path=str(self.non_repo_path))

            self.assertFalse(
                result["success"], f"{tool.__class__.__name__} should fail on non-repo"
            )
            self.assertEqual(result["error_type"], "NotGitRepository")


if __name__ == "__main__":
    unittest.main()
