#!/usr/bin/env python3
"""IABuilder CLI - Works from any project directory."""

import os
import sys

# Set API key from environment or user configuration
# Users should configure their API key via /configure-api command or environment variable

# Change to the directory from where the command was executed
working_directory = os.getcwd()

# Add the iabuilder package to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def main():
    """Main entry point for iabuilder."""
    try:
        from iabuilder.main import IABuilderApp
        app = IABuilderApp(working_directory=working_directory)
        app.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()