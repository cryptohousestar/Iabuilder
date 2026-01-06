"""Tests for Package Management tools in Groq CLI Custom."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from iabuilder.tools.package_tools import (
    DependencyAnalyzerTool,
    LockFileManagerTool,
    PackageInstallerTool,
    VirtualEnvironmentTool,
)


class TestPackageTools(unittest.TestCase):
    """Test cases for Package Management tools."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.work_dir = Path(self.test_dir) / "project"
        self.work_dir.mkdir()

        # Create sample package files
        self._create_sample_files()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_sample_files(self):
        """Create sample package files for testing."""
        # Create package.json
        package_json = {
            "name": "test-project",
            "version": "1.0.0",
            "dependencies": {"express": "^4.18.0", "lodash": "^4.17.21"},
            "devDependencies": {"jest": "^28.0.0", "nodemon": "^2.0.15"},
        }
        (self.work_dir / "package.json").write_text(json.dumps(package_json, indent=2))

        # Create requirements.txt
        requirements = ["requests==2.28.1", "flask==2.2.2", "pytest==7.1.2"]
        (self.work_dir / "requirements.txt").write_text("\n".join(requirements))

        # Create composer.json
        composer_json = {
            "name": "test/project",
            "require": {"php": ">=7.4", "symfony/framework-bundle": "^6.0"},
            "require-dev": {"phpunit/phpunit": "^9.0"},
        }
        (self.work_dir / "composer.json").write_text(
            json.dumps(composer_json, indent=2)
        )

        # Create Cargo.toml
        cargo_toml = """[package]
name = "test-project"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = "1.0"
serde = { version = "1.0", features = ["derive"] }

[dev-dependencies]
tokio-test = "0.4"
"""
        (self.work_dir / "Cargo.toml").write_text(cargo_toml)

    def test_package_installer_tool_detection(self):
        """Test PackageInstallerTool auto-detection."""
        tool = PackageInstallerTool()

        # Test auto-detection with package.json
        detected = tool._detect_package_manager(self.work_dir)
        self.assertEqual(detected, "npm")

        # Test with yarn.lock
        (self.work_dir / "yarn.lock").touch()
        detected = tool._detect_package_manager(self.work_dir)
        self.assertEqual(detected, "yarn")

        # Test detection priority
        os.remove(self.work_dir / "yarn.lock")
        detected = tool._detect_package_manager(self.work_dir)
        self.assertEqual(detected, "npm")

        # Test Python project detection
        python_dir = Path(self.test_dir) / "python_project"
        python_dir.mkdir()
        (python_dir / "main.py").touch()
        detected = tool._detect_package_manager(python_dir)
        self.assertEqual(detected, "pip")

        # Test Cargo detection
        cargo_dir = Path(self.test_dir) / "rust_project"
        cargo_dir.mkdir()
        (cargo_dir / "Cargo.toml").write_text(
            "[package]\nname = 'test'\nversion = '0.1.0'"
        )
        detected = tool._detect_package_manager(cargo_dir)
        self.assertEqual(detected, "cargo")

    @patch("subprocess.run")
    def test_package_installer_tool_availability_check(self, mock_run):
        """Test package manager availability check."""
        tool = PackageInstallerTool()

        # Test available package manager
        mock_run.return_value = Mock(returncode=0)
        self.assertTrue(tool._is_package_manager_available("npm"))

        # Test unavailable package manager
        mock_run.side_effect = FileNotFoundError()
        self.assertFalse(tool._is_package_manager_available("nonexistent"))

        # Test timeout
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)
        self.assertFalse(tool._is_package_manager_available("npm"))

    def test_package_installer_tool_install_suggestions(self):
        """Test install suggestions for package managers."""
        tool = PackageInstallerTool()

        suggestions = {
            "npm": "Install Node.js from https://nodejs.org/",
            "pip": "Install Python from https://python.org/",
            "composer": "Install Composer from https://getcomposer.org/",
            "cargo": "Install Rust from https://rustup.rs/",
        }

        for pm, expected in suggestions.items():
            self.assertEqual(tool._get_install_suggestion(pm), expected)

    @patch("subprocess.run")
    def test_package_installer_tool_npm_install(self, mock_run):
        """Test NPM package installation."""
        tool = PackageInstallerTool()

        # Mock successful installation
        mock_run.return_value = Mock(returncode=0, stdout="installed successfully")

        result = tool.execute(
            package_manager="npm",
            packages=["express"],
            working_directory=str(self.work_dir),
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["package_manager"], "npm")
        self.assertIn("express", result["packages"])

    @patch("subprocess.run")
    def test_package_installer_tool_pip_with_venv(self, mock_run):
        """Test pip installation with virtual environment."""
        tool = PackageInstallerTool()

        # Create mock venv
        venv_dir = self.work_dir / "venv"
        venv_dir.mkdir()
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir()
        pip_path = venv_bin / "pip"
        pip_path.touch()

        mock_run.return_value = Mock(returncode=0, stdout="installed successfully")

        result = tool.execute(
            package_manager="pip",
            packages=["requests"],
            working_directory=str(self.work_dir),
            virtual_env=True,
        )

        # Verify pip command was built correctly with venv
        pip_cmd = tool._build_pip_command("pip", ["requests"], self.work_dir, True)
        self.assertEqual(pip_cmd[0], str(pip_path))

    def test_dependency_analyzer_tool_detection(self):
        """Test DependencyAnalyzerTool package manager detection."""
        tool = DependencyAnalyzerTool()

        # Should use PackageInstallerTool's detection logic
        installer = PackageInstallerTool()
        detected = installer._detect_package_manager(self.work_dir)
        self.assertEqual(detected, "npm")

    @patch("subprocess.run")
    def test_dependency_analyzer_tool_npm_audit(self, mock_run):
        """Test NPM audit functionality."""
        tool = DependencyAnalyzerTool()

        # Mock npm audit response
        audit_response = {
            "vulnerabilities": {
                "lodash": {
                    "severity": "high",
                    "title": "Prototype Pollution",
                    "range": ">=1.0.0 <4.17.12",
                    "via": ["lodash"],
                }
            },
            "metadata": {"total": 1},
        }
        mock_run.return_value = Mock(returncode=0, stdout=json.dumps(audit_response))

        result = tool.execute(
            package_manager="npm",
            working_directory=str(self.work_dir),
            check_vulnerabilities=True,
            check_outdated=False,
        )

        self.assertTrue(result["success"])
        self.assertIn("vulnerabilities", result)
        vuln_result = result["vulnerabilities"]
        self.assertTrue(vuln_result["supported"])
        self.assertEqual(len(vuln_result["vulnerabilities"]), 1)
        self.assertEqual(vuln_result["vulnerabilities"][0]["package"], "lodash")
        self.assertEqual(vuln_result["vulnerabilities"][0]["severity"], "high")

    def test_dependency_analyzer_tool_severity_filter(self):
        """Test vulnerability severity filtering."""
        tool = DependencyAnalyzerTool()

        # Test severity level checking
        self.assertTrue(tool._should_include_severity("critical", "all"))
        self.assertTrue(tool._should_include_severity("high", "high"))
        self.assertTrue(tool._should_include_severity("critical", "high"))
        self.assertFalse(tool._should_include_severity("low", "high"))
        self.assertFalse(tool._should_include_severity("moderate", "high"))

    @patch("subprocess.run")
    def test_dependency_analyzer_tool_outdated_check(self, mock_run):
        """Test outdated packages check."""
        tool = DependencyAnalyzerTool()

        outdated_response = {
            "express": {
                "current": "4.17.1",
                "wanted": "4.18.0",
                "latest": "4.18.2",
                "location": "node_modules/express",
            }
        }
        mock_run.return_value = Mock(returncode=0, stdout=json.dumps(outdated_response))

        result = tool.execute(
            package_manager="npm",
            working_directory=str(self.work_dir),
            check_vulnerabilities=False,
            check_outdated=True,
        )

        self.assertTrue(result["success"])
        self.assertIn("outdated", result)
        outdated_result = result["outdated"]
        self.assertTrue(outdated_result["supported"])
        self.assertEqual(len(outdated_result["packages"]), 1)
        self.assertEqual(outdated_result["packages"][0]["name"], "express")

    def test_virtual_environment_tool_type_detection(self):
        """Test VirtualEnvironmentTool type detection."""
        tool = VirtualEnvironmentTool()

        # Test Python project detection
        python_dir = Path(self.test_dir) / "python_only"
        python_dir.mkdir()
        (python_dir / "main.py").touch()

        # Should detect Python for .py files
        result = tool.execute(
            action="info", environment_type="auto", working_directory=str(python_dir)
        )
        # The function should auto-detect Python type

        # Test Node.js project detection
        result = tool.execute(
            action="info",
            environment_type="auto",
            working_directory=str(self.work_dir),  # Has package.json
        )
        # Should detect Node.js due to package.json

    @patch("subprocess.run")
    def test_virtual_environment_tool_python_create(self, mock_run):
        """Test Python virtual environment creation."""
        tool = VirtualEnvironmentTool()

        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = tool.execute(
            action="create",
            environment_type="python",
            environment_name="test_env",
            working_directory=str(self.work_dir),
        )

        # Should attempt to create venv
        mock_run.assert_called_with(
            ["python3", "-m", "venv", str(self.work_dir / "test_env")],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_virtual_environment_tool_python_list(self):
        """Test listing Python virtual environments."""
        tool = VirtualEnvironmentTool()

        # Create mock venv directory
        venv_dir = self.work_dir / "venv"
        venv_dir.mkdir()
        (venv_dir / "pyvenv.cfg").touch()

        another_venv = self.work_dir / "test_env"
        another_venv.mkdir()
        (another_venv / "pyvenv.cfg").touch()

        result = tool.execute(
            action="list",
            environment_type="python",
            working_directory=str(self.work_dir),
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["total_environments"], 2)
        env_names = [env["name"] for env in result["virtual_environments"]]
        self.assertIn("venv", env_names)
        self.assertIn("test_env", env_names)

    def test_virtual_environment_tool_node_nvmrc(self):
        """Test Node.js environment with .nvmrc."""
        tool = VirtualEnvironmentTool()

        # Test creating .nvmrc
        result = tool.execute(
            action="create",
            environment_type="node",
            node_version="18.16.0",
            working_directory=str(self.work_dir),
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["nvmrc_created"])
        self.assertEqual(result["node_version"], "18.16.0")

        # Verify .nvmrc was created
        nvmrc_path = self.work_dir / ".nvmrc"
        self.assertTrue(nvmrc_path.exists())
        self.assertEqual(nvmrc_path.read_text().strip(), "18.16.0")

        # Test reading .nvmrc info
        result = tool.execute(
            action="info", environment_type="node", working_directory=str(self.work_dir)
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["nvmrc_exists"])
        self.assertEqual(result["node_version"], "18.16.0")

    def test_lock_file_manager_tool_detection(self):
        """Test LockFileManagerTool lock file detection."""
        tool = LockFileManagerTool()

        # Create lock files
        (self.work_dir / "package-lock.json").touch()
        (self.work_dir / "yarn.lock").touch()

        lock_files = tool._detect_lock_files(self.work_dir)

        self.assertIn("npm", lock_files)
        self.assertIn("yarn", lock_files)
        self.assertEqual(lock_files["npm"], self.work_dir / "package-lock.json")
        self.assertEqual(lock_files["yarn"], self.work_dir / "yarn.lock")

    def test_lock_file_manager_tool_analyze(self):
        """Test lock file analysis."""
        tool = LockFileManagerTool()

        # Create sample npm lock file
        npm_lock = {
            "name": "test-project",
            "version": "1.0.0",
            "lockfileVersion": 2,
            "packages": {
                "": {"name": "test-project", "version": "1.0.0"},
                "node_modules/express": {"version": "4.18.0"},
            },
            "dependencies": {"express": {"version": "4.18.0"}},
        }
        lock_file_path = self.work_dir / "package-lock.json"
        lock_file_path.write_text(json.dumps(npm_lock, indent=2))

        result = tool.execute(action="analyze", working_directory=str(self.work_dir))

        self.assertTrue(result["success"])
        self.assertEqual(result["total_lock_files"], 1)
        self.assertIn("npm", result["lock_files"])

        npm_analysis = result["lock_files"]["npm"]
        self.assertTrue(npm_analysis["exists"])
        self.assertEqual(npm_analysis["format"], "npm")
        self.assertEqual(npm_analysis["lockfile_version"], 2)
        self.assertEqual(npm_analysis["packages_count"], 2)

    def test_lock_file_manager_tool_yarn_analysis(self):
        """Test Yarn lock file analysis."""
        tool = LockFileManagerTool()

        # Create sample yarn lock file
        yarn_lock_content = """# THIS IS AN AUTOGENERATED FILE. DO NOT EDIT THIS FILE DIRECTLY.
# yarn lockfile v1

express@^4.18.0:
  version "4.18.0"
  resolved "https://registry.yarnpkg.com/express/-/express-4.18.0.tgz"
  integrity sha512-...
  dependencies:
    accepts "~1.3.8"

accepts@~1.3.8:
  version "1.3.8"
  resolved "https://registry.yarnpkg.com/accepts/-/accepts-1.3.8.tgz"
"""
        yarn_lock_path = self.work_dir / "yarn.lock"
        yarn_lock_path.write_text(yarn_lock_content)

        result = tool.execute(
            action="analyze",
            package_manager="yarn",
            working_directory=str(self.work_dir),
        )

        self.assertTrue(result["success"])
        yarn_analysis = result["lock_files"]["yarn"]
        self.assertEqual(yarn_analysis["format"], "yarn")
        self.assertEqual(yarn_analysis["packages_count"], 2)  # express and accepts

    @patch("subprocess.run")
    def test_lock_file_manager_tool_update(self, mock_run):
        """Test lock file update."""
        tool = LockFileManagerTool()

        (self.work_dir / "package-lock.json").touch()
        mock_run.return_value = Mock(returncode=0, stdout="updated successfully")

        result = tool.execute(
            action="update", package_manager="npm", working_directory=str(self.work_dir)
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["package_manager"], "npm")
        mock_run.assert_called_with(
            ["npm", "install"],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

    def test_lock_file_manager_tool_clean(self):
        """Test lock file cleaning."""
        tool = LockFileManagerTool()

        # Create lock files
        npm_lock = self.work_dir / "package-lock.json"
        yarn_lock = self.work_dir / "yarn.lock"
        npm_lock.touch()
        yarn_lock.touch()

        lock_files = {"npm": npm_lock, "yarn": yarn_lock}

        result = tool.execute(action="clean", working_directory=str(self.work_dir))

        self.assertTrue(result["success"])
        self.assertEqual(len(result["cleaned_files"]), 2)

        # Verify files were removed
        self.assertFalse(npm_lock.exists())
        self.assertFalse(yarn_lock.exists())

    def test_lock_file_manager_tool_validate(self):
        """Test lock file validation."""
        tool = LockFileManagerTool()

        # Create package and lock files
        (self.work_dir / "package-lock.json").touch()
        # package.json already exists from setUp

        result = tool.execute(action="validate", working_directory=str(self.work_dir))

        self.assertTrue(result["success"])
        npm_validation = result["validation_results"]["npm"]
        self.assertTrue(npm_validation["valid"])
        self.assertTrue(npm_validation["lock_exists"])
        self.assertTrue(npm_validation["package_exists"])

    def test_lock_file_manager_tool_compare(self):
        """Test lock file comparison."""
        tool = LockFileManagerTool()

        # Create two different lock files
        lock_file1 = self.work_dir / "package-lock.json"
        lock_file2 = self.work_dir / "package-lock-backup.json"

        lock_content1 = '{"name": "test", "version": "1.0.0"}'
        lock_content2 = '{"name": "test", "version": "1.0.1"}'

        lock_file1.write_text(lock_content1)
        lock_file2.write_text(lock_content2)

        result = tool.execute(
            action="compare",
            compare_with=str(lock_file2),
            working_directory=str(self.work_dir),
        )

        self.assertTrue(result["success"])
        npm_comparison = result["comparison_results"]["npm"]
        self.assertTrue(npm_comparison["compared"])
        self.assertFalse(npm_comparison["identical"])


class TestPackageToolsIntegration(unittest.TestCase):
    """Test integration between package management tools."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.work_dir = Path(self.test_dir) / "integration_project"
        self.work_dir.mkdir()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_package_workflow_integration(self):
        """Test complete package management workflow."""
        # Create project files
        package_json = {
            "name": "integration-test",
            "version": "1.0.0",
            "dependencies": {"express": "^4.18.0"},
        }
        (self.work_dir / "package.json").write_text(json.dumps(package_json))

        installer = PackageInstallerTool()
        analyzer = DependencyAnalyzerTool()
        lock_manager = LockFileManagerTool()

        # Test package manager detection consistency
        detected_pm_installer = installer._detect_package_manager(self.work_dir)
        self.assertEqual(detected_pm_installer, "npm")

        # Test lock file detection
        (self.work_dir / "package-lock.json").touch()
        lock_files = lock_manager._detect_lock_files(self.work_dir)
        self.assertIn("npm", lock_files)

        # Test lock file analysis
        result = lock_manager.execute(
            action="analyze", working_directory=str(self.work_dir)
        )
        self.assertTrue(result["success"])

    @patch("subprocess.run")
    def test_virtual_env_and_package_install_integration(self, mock_run):
        """Test virtual environment creation and package installation."""
        # Create Python project
        (self.work_dir / "main.py").touch()
        (self.work_dir / "requirements.txt").write_text("requests==2.28.1")

        venv_tool = VirtualEnvironmentTool()
        installer = PackageInstallerTool()

        # Mock subprocess calls
        mock_run.return_value = Mock(returncode=0, stdout="success")

        # Create virtual environment
        venv_result = venv_tool.execute(
            action="create",
            environment_type="python",
            working_directory=str(self.work_dir),
        )

        # Should detect Python project and create venv
        self.assertTrue(venv_result["success"])


class TestPackageToolsErrorHandling(unittest.TestCase):
    """Test error handling in package management tools."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_package_installer_missing_directory(self):
        """Test handling of missing working directory."""
        tool = PackageInstallerTool()

        result = tool.execute(
            package_manager="npm",
            packages=["express"],
            working_directory="/nonexistent/directory",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "DirectoryNotFound")

    def test_package_installer_no_detection(self):
        """Test handling when no package manager can be detected."""
        tool = PackageInstallerTool()
        empty_dir = Path(self.test_dir) / "empty"
        empty_dir.mkdir()

        result = tool.execute(
            package_manager="auto",
            packages=["express"],
            working_directory=str(empty_dir),
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "PackageManagerNotDetected")

    def test_dependency_analyzer_unsupported_package_manager(self):
        """Test handling of unsupported package managers."""
        tool = DependencyAnalyzerTool()

        # Test with package manager that doesn't support vulnerability checking
        result = tool._check_vulnerabilities(
            "unsupported_pm", Path(self.test_dir), "all"
        )
        self.assertFalse(result["supported"])

    def test_virtual_environment_tool_invalid_action(self):
        """Test handling of invalid actions."""
        tool = VirtualEnvironmentTool()

        result = tool.execute(
            action="invalid_action", working_directory=str(self.test_dir)
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "UnsupportedAction")

    def test_lock_file_manager_no_lock_files(self):
        """Test handling when no lock files are found."""
        tool = LockFileManagerTool()
        empty_dir = Path(self.test_dir) / "no_locks"
        empty_dir.mkdir()

        result = tool.execute(
            action="analyze", package_manager="auto", working_directory=str(empty_dir)
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "NoLockFilesFound")

    def test_lock_file_manager_missing_comparison_file(self):
        """Test handling of missing comparison file."""
        tool = LockFileManagerTool()
        work_dir = Path(self.test_dir) / "compare_test"
        work_dir.mkdir()
        (work_dir / "package-lock.json").touch()

        result = tool.execute(
            action="compare",
            compare_with="/nonexistent/file.json",
            working_directory=str(work_dir),
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "ComparisonFileNotFound")


if __name__ == "__main__":
    unittest.main()
