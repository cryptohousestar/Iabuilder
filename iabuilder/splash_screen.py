"""Splash screen for IABuilder."""

from datetime import datetime
from typing import Dict, List, Optional


class SplashScreen:
    """Generates splash screen for IABuilder startup."""

    @staticmethod
    def get_splash(
        providers: Optional[List[Dict]] = None,
        current_model: Optional[str] = None,
        detected_tools: Optional[int] = None,
        detected_context: Optional[List[str]] = None,
    ) -> str:
        """Generate splash screen with dynamic information.

        Args:
            providers: List of configured providers with their status
            current_model: Currently active model name
            detected_tools: Number of tools loaded
            detected_context: List of detected project contexts (e.g., ['Python', 'Git'])

        Returns:
            Formatted splash screen string
        """
        lines = []

        # Main logo
        lines.append("")
        lines.append("")
        lines.append("        ╭────────────────────────────────────────────────────────────────────╮")
        lines.append("        │                                                                    │")
        lines.append("        │   ██╗ █████╗ ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗  │")
        lines.append("        │   ██║██╔══██╗██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗ │")
        lines.append("        │   ██║███████║██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝ │")
        lines.append("        │   ██║██╔══██║██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗ │")
        lines.append("        │   ██║██║  ██║██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║ │")
        lines.append("        │   ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝ │")
        lines.append("        │                                                                    │")
        lines.append("        │              🤖 Intelligent Architecture Builder 🚀                │")
        lines.append("        │                        Version 3.0.0                               │")
        lines.append("        │                                                                    │")
        lines.append("        ╰────────────────────────────────────────────────────────────────────╯")
        lines.append("")

        # Provider status
        if providers:
            lines.append("        🔄 Checking configured providers...")
            lines.append("")

            for provider in providers:
                status_icon = "✅" if provider.get("status") == "active" else "⚠️"
                name = provider.get("name", "Unknown")
                model_count = provider.get("model_count", 0)
                latency = provider.get("latency_ms", 0)

                lines.append(
                    f"        {status_icon} {name:<15} {model_count} models    ({latency}ms)"
                )

            lines.append("")

        # Detected context
        if detected_context:
            context_str = " • ".join(detected_context)
            lines.append(f"        📋 Detected: {context_str}")

        # Tools loaded
        if detected_tools:
            lines.append(f"        🧰 Loaded {detected_tools} specialized tools")

        # Current model
        if current_model:
            lines.append("")
            lines.append(f"        Current model: {current_model}")

        lines.append("")
        lines.append(
            "        ──────────────────────────────────────────────────────────────────────"
        )
        lines.append("")
        lines.append(
            "        💡 Tip: Try /help to see available commands or just start chatting!"
        )
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def get_minimal_splash(version: str = "3.0.0") -> str:
        """Generate minimal splash screen (fast startup).

        Args:
            version: Version string

        Returns:
            Minimal splash screen string
        """
        lines = []
        lines.append("")
        lines.append("        ╭────────────────────────────────────────────────────────────────────╮")
        lines.append("        │                                                                    │")
        lines.append("        │   ██╗ █████╗ ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗  │")
        lines.append("        │   ██║██╔══██╗██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗ │")
        lines.append("        │   ██║███████║██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝ │")
        lines.append("        │   ██║██╔══██║██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗ │")
        lines.append("        │   ██║██║  ██║██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║ │")
        lines.append("        │   ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝ │")
        lines.append("        │                                                                    │")
        lines.append("        │              🤖 Intelligent Architecture Builder 🚀                │")
        lines.append(f"        │                        Version {version:<8}                           │")
        lines.append("        │                                                                    │")
        lines.append("        ╰────────────────────────────────────────────────────────────────────╯")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def get_greeting() -> str:
        """Get time-appropriate greeting.

        Returns:
            Greeting string with emoji
        """
        hour = datetime.now().hour

        if 5 <= hour < 12:
            return "☀️  Good morning!"
        elif 12 <= hour < 18:
            return "☀️  Good afternoon!"
        else:
            return "🌙 Good evening!"

    @staticmethod
    def get_first_run_splash() -> str:
        """Generate splash screen for first-time users.

        Returns:
            First run splash with welcome message
        """
        lines = []
        lines.append("")
        lines.append("        ╭────────────────────────────────────────────────────────────────────╮")
        lines.append("        │                                                                    │")
        lines.append("        │   ██╗ █████╗ ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗  │")
        lines.append("        │   ██║██╔══██╗██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗ │")
        lines.append("        │   ██║███████║██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝ │")
        lines.append("        │   ██║██╔══██║██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗ │")
        lines.append("        │   ██║██║  ██║██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║ │")
        lines.append("        │   ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝ │")
        lines.append("        │                                                                    │")
        lines.append("        │              🤖 Intelligent Architecture Builder 🚀                │")
        lines.append("        │                        Version 3.0.0                               │")
        lines.append("        │                                                                    │")
        lines.append("        ╰────────────────────────────────────────────────────────────────────╯")
        lines.append("")
        lines.append("        🎉 Welcome to IABuilder!")
        lines.append("")
        lines.append("        Let's get you started:")
        lines.append("")
        lines.append("        1. Configure an API provider:")
        lines.append("           /configure-api groq      → Free & fast (recommended)")
        lines.append("           /configure-api google    → Google AI (Gemini)")
        lines.append("           /configure-api openai    → OpenAI (GPT-4)")
        lines.append("")
        lines.append("        2. Start chatting:")
        lines.append("           Just type your question or request!")
        lines.append("")
        lines.append("        3. Explore commands:")
        lines.append("           /help                    → See all available commands")
        lines.append("")
        lines.append(
            "        ──────────────────────────────────────────────────────────────────────"
        )
        lines.append("")

        return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    # Test splash screen
    splash = SplashScreen()

    # Full splash with providers
    providers = [
        {"name": "Groq", "status": "active", "model_count": 8, "latency_ms": 127},
        {"name": "Google AI", "status": "active", "model_count": 4, "latency_ms": 203},
        {
            "name": "OpenRouter",
            "status": "active",
            "model_count": 120,
            "latency_ms": 451,
        },
    ]

    print(
        splash.get_splash(
            providers=providers,
            current_model="llama-3.3-70b-versatile (Groq)",
            detected_tools=22,
            detected_context=["🐍 Python", "🌿 Git", "📦 npm", "🗄️ PostgreSQL"],
        )
    )

    print("\n" + "=" * 80 + "\n")

    # Minimal splash
    print(splash.get_minimal_splash())

    print("\n" + "=" * 80 + "\n")

    # First run splash
    print(splash.get_first_run_splash())
