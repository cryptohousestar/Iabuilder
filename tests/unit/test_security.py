"""Tests for security modules."""

import unittest
import tempfile
import os
from pathlib import Path

from iabuilder.security import (
    get_credential_manager,
    get_input_validator,
)
from iabuilder.errors import ValidationError


class TestCredentialManager(unittest.TestCase):
    """Test credential management."""

    def setUp(self):
        """Set up test environment."""
        self.cred_manager = get_credential_manager()

    def test_api_key_validation(self):
        """Test API key format validation."""
        # Valid Groq key
        valid_key = "gsk_" + "a" * 40
        self.assertTrue(
            self.cred_manager._validate_api_key("groq", valid_key)
        )

        # Invalid key
        self.assertFalse(
            self.cred_manager._validate_api_key("groq", "invalid")
        )

    def test_list_providers(self):
        """Test listing providers."""
        providers = self.cred_manager.list_providers()
        self.assertIsInstance(providers, list)

    def test_provider_name_normalization(self):
        """Test that provider names are normalized to lowercase."""
        # Use a test provider that won't conflict with real ones
        test_provider = "TEST_PROVIDER"
        test_key = "test_key_" + "a" * 40

        # Save with uppercase
        self.cred_manager.save_api_key(test_provider, test_key)

        # Retrieve with lowercase
        retrieved = self.cred_manager.get_api_key(test_provider.lower())
        self.assertEqual(retrieved, test_key)

        # Cleanup
        self.cred_manager.delete_api_key(test_provider.lower())


class TestInputValidator(unittest.TestCase):
    """Test input validation."""

    def setUp(self):
        """Set up test environment."""
        self.validator = get_input_validator()

    def test_file_path_validation(self):
        """Test file path validation."""
        # Valid path
        valid_path = "/tmp/test.txt"
        result = self.validator.validate_file_path(valid_path, must_exist=False)
        self.assertIsInstance(result, Path)

        # Empty path
        with self.assertRaises(ValidationError):
            self.validator.validate_file_path("")

    def test_command_validation(self):
        """Test command validation."""
        # Valid command
        valid_cmd = "ls -la"
        result = self.validator.validate_command(valid_cmd)
        self.assertEqual(result, valid_cmd)

        # Command with dangerous characters
        with self.assertRaises(ValidationError):
            self.validator.validate_command("rm -rf; cat /etc/passwd")

        # Command with pipe (not allowed by default)
        with self.assertRaises(ValidationError):
            self.validator.validate_command("cat file | grep test")

        # Command with pipe (allowed)
        result = self.validator.validate_command(
            "cat file | grep test",
            allow_pipes=True
        )
        self.assertEqual(result, "cat file | grep test")

    def test_api_key_validation(self):
        """Test API key validation."""
        # Valid Groq key
        valid_key = "gsk_" + "a" * 40
        result = self.validator.validate_api_key("groq", valid_key)
        self.assertEqual(result, valid_key)

        # Too short
        with self.assertRaises(ValidationError):
            self.validator.validate_api_key("groq", "short")

        # Wrong format
        with self.assertRaises(ValidationError):
            self.validator.validate_api_key("groq", "sk_wrongprefix" + "a" * 40)

    def test_filename_sanitization(self):
        """Test filename sanitization."""
        # Path traversal attempt
        dangerous = "../../../etc/passwd"
        result = self.validator.sanitize_filename(dangerous)
        self.assertEqual(result, "passwd")

        # Valid filename
        valid = "myfile.txt"
        result = self.validator.sanitize_filename(valid)
        self.assertEqual(result, "myfile.txt")

    def test_model_name_validation(self):
        """Test model name validation."""
        # Valid model names
        valid_names = [
            "llama-3.3-70b-versatile",
            "gpt-4",
            "claude-3-opus",
            "mixtral-8x7b"
        ]

        for name in valid_names:
            result = self.validator.validate_model_name(name)
            self.assertEqual(result, name)

        # Invalid model name
        with self.assertRaises(ValidationError):
            self.validator.validate_model_name("model;rm -rf /")

    def test_url_validation(self):
        """Test URL validation."""
        # Valid URLs
        valid_urls = [
            "https://api.groq.com/v1/chat",
            "http://localhost:8000",
        ]

        for url in valid_urls:
            result = self.validator.validate_url(url)
            self.assertEqual(result, url)

        # Invalid URL
        with self.assertRaises(ValidationError):
            self.validator.validate_url("not a url")

        # Invalid scheme
        with self.assertRaises(ValidationError):
            self.validator.validate_url(
                "ftp://server.com",
                allowed_schemes=["http", "https"]
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
