#!/usr/bin/env python3
"""Launcher for iabuilder that works from any directory."""

import logging
import os
import site
import sys
from pathlib import Path

# Configure logging
log_dir = os.path.expanduser("~/.iabuilder/logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=os.path.join(log_dir, "iabuilder.log"),
)
logger = logging.getLogger("iabuilder")

# API key should be set via environment variable or user configuration
# Users should configure their API key via /configure-api command

# Get the working directory (where the command was executed from)
working_directory = os.environ.get("IABUILDER_WORKING_DIR", os.getcwd())
logger.info(f"Working directory: {working_directory}")

# Change to the CLI directory to import modules
cli_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, cli_dir)
logger.info(f"CLI directory: {cli_dir}")

# Check virtual environment
venv_dir = os.path.join(cli_dir, "venv")
venv_site_packages = os.path.join(
    venv_dir,
    "lib",
    f"python{sys.version_info.major}.{sys.version_info.minor}",
    "site-packages",
)

if os.path.exists(venv_site_packages):
    logger.info(f"Using virtual environment at: {venv_dir}")
    # Add virtual environment site-packages to path if not already there
    if venv_site_packages not in sys.path:
        sys.path.insert(0, venv_site_packages)
        site.addsitedir(venv_site_packages)
else:
    logger.warning(f"Virtual environment not found at: {venv_dir}")

# Ensure the config directory exists
config_dir = os.path.expanduser("~/.iabuilder")
os.makedirs(config_dir, exist_ok=True)

# Ensure logs directory exists
os.makedirs(os.path.join(config_dir, "logs"), exist_ok=True)
os.makedirs(os.path.join(config_dir, "process_logs"), exist_ok=True)

# Change back to working directory for file operations
os.chdir(working_directory)


def main():
    """Launch iabuilder."""
    try:
        print(f"🔄 Working directory: {working_directory}")
        print(f"🚀 Launching IABuilder CLI...")

        # Check for required packages
        try:
            import groq
            import prompt_toolkit
            import rich
        except ImportError as e:
            print(f"❌ Error: Missing required package: {e}")
            print("\nAttempting to install dependencies...")

            # Try to install dependencies
            import subprocess

            try:
                # Install required packages
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        os.path.join(cli_dir, "requirements.txt"),
                    ]
                )

                # Explicitly install tiktoken (common issue)
                try:
                    print("Installing tiktoken explicitly...")
                    subprocess.check_call(
                        [
                            sys.executable,
                            "-m",
                            "pip",
                            "install",
                            "tiktoken",
                        ]
                    )
                except Exception:
                    pass  # Continue even if tiktoken install fails

                print("✅ Dependencies installed successfully. Restarting...")

                # Re-import after installation
                import importlib

                import groq
                import prompt_toolkit
                import rich

                try:
                    import tiktoken
                except ImportError:
                    print(
                        "⚠️ Warning: tiktoken module not available. Some features may be limited."
                    )
            except Exception as install_error:
                print(f"❌ Error installing dependencies: {install_error}")
                print("\nPlease run: pip install -r requirements.txt")
                sys.exit(1)

        # Import and initialize the application
        from iabuilder.main import IABuilderApp

        # Check Groq API key
        if not os.environ.get("GROQ_API_KEY"):
            print("❌ Error: GROQ_API_KEY environment variable is not set")
            sys.exit(1)

        # Initialize the app
        app = IABuilderApp(working_directory=working_directory)

        # Run the application
        app.run()
    except ModuleNotFoundError as e:
        print(f"❌ Error: Could not load required modules: {e}")
        print(
            "Please make sure you have installed all dependencies with 'pip install -r requirements.txt'"
        )
        logger.error(f"Module error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback

        error_traceback = traceback.format_exc()
        print(error_traceback)
        logger.error(f"Fatal error: {e}\n{error_traceback}")
        sys.exit(1)


if __name__ == "__main__":
    main()
