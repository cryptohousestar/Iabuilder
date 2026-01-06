"""Tests for core.bootstrap module."""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from iabuilder.core.bootstrap import AppBootstrap


class TestAppBootstrap(unittest.TestCase):
    """Test AppBootstrap class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test bootstrap initialization."""
        bootstrap = AppBootstrap(working_directory=self.temp_dir)

        self.assertIsNotNone(bootstrap.renderer)
        self.assertIsNotNone(bootstrap.error_handler)
        self.assertEqual(bootstrap.working_directory, Path(self.temp_dir).resolve())

    def test_working_directory_default(self):
        """Test default working directory (current dir)."""
        # Save and restore directory safely
        try:
            original_cwd = os.getcwd()
        except FileNotFoundError:
            # Current directory was deleted, use temp
            original_cwd = self.temp_dir

        try:
            os.chdir(self.temp_dir)
            bootstrap = AppBootstrap()
            self.assertEqual(bootstrap.working_directory, Path(self.temp_dir).resolve())
        finally:
            try:
                os.chdir(original_cwd)
            except (FileNotFoundError, OSError):
                # Original directory doesn't exist, stay in temp
                os.chdir(self.temp_dir)

    def test_working_directory_custom(self):
        """Test custom working directory."""
        bootstrap = AppBootstrap(working_directory=self.temp_dir)
        self.assertEqual(bootstrap.working_directory, Path(self.temp_dir).resolve())

    def test_splash_screen_first_run(self):
        """Test splash screen on first run."""
        # Create a non-existent config path
        with patch('iabuilder.core.bootstrap.Path.home') as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            bootstrap = AppBootstrap(working_directory=self.temp_dir)

            is_first_run = bootstrap.show_splash_screen()
            self.assertTrue(is_first_run)

    def test_initialize_config(self):
        """Test configuration initialization."""
        with patch('iabuilder.core.bootstrap.get_config_manager') as mock_config_mgr, \
             patch('iabuilder.core.bootstrap.load_config') as mock_load_config, \
             patch('iabuilder.core.bootstrap.get_multi_provider_config_manager') as mock_provider, \
             patch('iabuilder.core.bootstrap.get_model_registry') as mock_registry:

            mock_config_mgr.return_value = Mock()
            mock_load_config.return_value = Mock()
            mock_provider.return_value = Mock()
            mock_registry.return_value = Mock()

            bootstrap = AppBootstrap(working_directory=self.temp_dir)
            result = bootstrap.initialize_config()

            self.assertEqual(len(result), 4)
            self.assertIsNotNone(result[0])  # config_manager
            self.assertIsNotNone(result[1])  # config
            self.assertIsNotNone(result[2])  # provider_config
            self.assertIsNotNone(result[3])  # model_registry

    def test_explore_project_success(self):
        """Test project exploration."""
        # Create some test files
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text("# test file")

        bootstrap = AppBootstrap(working_directory=self.temp_dir)
        project_explorer, project_context = bootstrap.explore_project()

        self.assertIsNotNone(project_explorer)
        self.assertIsInstance(project_context, dict)

    def test_explore_project_failure(self):
        """Test project exploration with error."""
        with patch('iabuilder.core.bootstrap.ProjectExplorer') as mock_explorer:
            mock_explorer.side_effect = Exception("Test error")

            bootstrap = AppBootstrap(working_directory=self.temp_dir)
            project_explorer, project_context = bootstrap.explore_project()

            self.assertIsNone(project_explorer)
            self.assertEqual(project_context, {})

    def test_initialize_components(self):
        """Test component initialization."""
        mock_config = Mock()
        mock_config.auto_save = True
        mock_config.api_key = "test_key"
        mock_config.default_model = "test_model"

        bootstrap = AppBootstrap(working_directory=self.temp_dir)
        conversation, cli, client, intent_classifier = bootstrap.initialize_components(mock_config)

        self.assertIsNotNone(conversation)
        self.assertIsNotNone(cli)
        self.assertIsNotNone(client)
        self.assertIsNotNone(intent_classifier)

    def test_setup_signal_handlers(self):
        """Test signal handler setup."""
        cleanup_called = []

        def cleanup_callback():
            cleanup_called.append(True)

        bootstrap = AppBootstrap(working_directory=self.temp_dir)
        # Just verify it doesn't raise an exception
        bootstrap.setup_signal_handlers(cleanup_callback)

        # Signal handlers are set up but we can't easily test the actual signals
        # without sending actual signals to the process

    def test_show_provider_status_with_providers(self):
        """Test showing provider status when providers exist."""
        mock_provider_config = Mock()
        mock_provider_config.list_providers.return_value = ["groq", "openai"]
        mock_provider_config.get_active_provider.return_value = "groq"

        bootstrap = AppBootstrap(working_directory=self.temp_dir)
        # Should not raise exception
        bootstrap.show_provider_status(mock_provider_config)

    def test_show_provider_status_no_providers(self):
        """Test showing provider status when no providers configured."""
        mock_provider_config = Mock()
        mock_provider_config.list_providers.return_value = []

        bootstrap = AppBootstrap(working_directory=self.temp_dir)
        # Should not raise exception
        bootstrap.show_provider_status(mock_provider_config)


if __name__ == '__main__':
    unittest.main(verbosity=2)
