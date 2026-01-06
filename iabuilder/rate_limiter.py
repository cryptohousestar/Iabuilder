"""Rate limiting system for Groq API to handle TPM (tokens per minute) limits."""

import time
import threading
from collections import deque
from typing import Optional
from dataclasses import dataclass

from .model_limits import get_model_limits, get_recommended_buffer_tokens


@dataclass
class TokenUsage:
    """Represents a token usage event."""
    timestamp: float
    tokens: int


class RateLimiter:
    """Intelligent rate limiter with per-provider and per-model limits."""

    def __init__(self, model_name: str = "llama-3.3-70b-versatile", tier: str = "free", provider: str = "groq"):
        """
        Initialize rate limiter with model-specific limits.

        Args:
            model_name: Name of the model being used
            tier: "free" or "paid" tier
            provider: Provider name (groq, openrouter, openai, etc.)
        """
        self.model_name = model_name
        self.tier = tier
        self.provider = provider.lower() if provider else "groq"

        # Get model-specific limits (provider-aware)
        self.limits = get_model_limits(model_name, tier, self.provider)
        self.buffer_tokens = get_recommended_buffer_tokens(model_name)

        # Set effective limits (actual limits minus buffer for safety)
        self.tpm_limit = self.limits.tpm
        self.rpm_limit = self.limits.rpm
        self.effective_tpm = self.tpm_limit - self.buffer_tokens
        self.effective_rpm = max(1, self.rpm_limit - 2)  # Keep 2 request buffer

        # Thread-safe storage for token usage
        self.usage_history = deque()
        self.request_history = deque()  # Track requests separately
        self.lock = threading.Lock()

        # Current minute tracking
        self.current_minute = int(time.time() // 60)
        self.tokens_this_minute = 0
        self.requests_this_minute = 0

    def update_model(self, model_name: str, tier: str = "free", provider: str = None):
        """Update limits when model or provider changes.

        Args:
            model_name: New model name
            tier: "free" or "paid" tier
            provider: Provider name (groq, openrouter, etc.)
        """
        with self.lock:
            self.model_name = model_name
            self.tier = tier
            if provider:
                self.provider = provider.lower()

            # Get new limits (provider-aware)
            self.limits = get_model_limits(model_name, tier, self.provider)
            self.buffer_tokens = get_recommended_buffer_tokens(model_name)

            # Update effective limits
            self.tpm_limit = self.limits.tpm
            self.rpm_limit = self.limits.rpm
            self.effective_tpm = self.tpm_limit - self.buffer_tokens
            self.effective_rpm = max(1, self.rpm_limit - 2)

            print(f"📊 Rate limits for {self.provider.upper()}/{model_name}:")
            print(f"   TPM: {self.tpm_limit:,} | RPM: {self.rpm_limit}")

    def can_make_request(self, estimated_tokens: int) -> bool:
        """
        Check if a request can be made without exceeding limits.

        Args:
            estimated_tokens: Estimated tokens for the request

        Returns:
            True if request can proceed, False if should wait
        """
        with self.lock:
            self._cleanup_old_entries()

            # Check RPM limit (requests per minute)
            if self.requests_this_minute >= self.effective_rpm:
                return False

            # Check TPM limit (tokens per minute)
            if self.tokens_this_minute + estimated_tokens > self.effective_tpm:
                return False

            return True

    def record_usage(self, tokens_used: int):
        """
        Record token and request usage after a successful request.

        Args:
            tokens_used: Actual tokens used in the request
        """
        with self.lock:
            now = time.time()

            # Record token usage
            self.usage_history.append(TokenUsage(timestamp=now, tokens=tokens_used))
            self.tokens_this_minute += tokens_used

            # Record request
            self.request_history.append(now)
            self.requests_this_minute += 1

    def wait_if_needed(self, estimated_tokens: int, show_progress: bool = True) -> bool:
        """
        Wait if necessary to avoid rate limits with intelligent delays.

        Args:
            estimated_tokens: Estimated tokens for upcoming request
            show_progress: Whether to show waiting progress

        Returns:
            True if waited, False if no wait was needed
        """
        if self.can_make_request(estimated_tokens):
            return False

        # Calculate wait time (until next minute starts)
        current_time = time.time()
        next_minute = (int(current_time // 60) + 1) * 60
        wait_seconds = int(next_minute - current_time)

        if show_progress:
            # Instead of technical messages, show "thinking..." for natural flow
            self._show_thinking_progress(wait_seconds)

        # Reset counter for new minute
        with self.lock:
            self.tokens_this_minute = 0

        return True

    def estimate_tokens(self, messages: list, tools: Optional[list] = None) -> int:
        """
        Estimate tokens for a request.

        Args:
            messages: Chat messages
            tools: Optional tools being provided

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        total_chars = 0

        for msg in messages:
            if isinstance(msg, dict) and 'content' in msg:
                content = msg.get('content', '')
                if content:
                    total_chars += len(str(content))

        # Add tool definitions if present
        if tools:
            for tool in tools:
                total_chars += len(str(tool)) * 2  # Tools are more complex

        # Convert to tokens (rough estimate)
        estimated_tokens = total_chars // 4

        # Add buffer for safety
        return max(estimated_tokens, 100)  # Minimum 100 tokens

    def get_current_usage(self) -> dict:
        """
        Get current token and request usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        with self.lock:
            self._cleanup_old_entries()

            tpm_percentage = (self.tokens_this_minute / self.effective_tpm) * 100 if self.effective_tpm > 0 else 0
            rpm_percentage = (self.requests_this_minute / self.effective_rpm) * 100 if self.effective_rpm > 0 else 0

            return {
                "model": self.model_name,
                "tier": self.tier,
                "tokens_this_minute": self.tokens_this_minute,
                "requests_this_minute": self.requests_this_minute,
                "effective_tpm": self.effective_tpm,
                "effective_rpm": self.effective_rpm,
                "tpm_limit": self.tpm_limit,
                "rpm_limit": self.rpm_limit,
                "tpm_usage_percentage": tpm_percentage,
                "rpm_usage_percentage": rpm_percentage,
                "can_make_request": self.tokens_this_minute < self.effective_tpm and self.requests_this_minute < self.effective_rpm,
                "token_entries_count": len(self.usage_history),
                "request_entries_count": len(self.request_history)
            }

    def _cleanup_old_entries(self):
        """Clean up entries from previous minutes."""
        current_minute = int(time.time() // 60)

        # If we've moved to a new minute, reset counters
        if current_minute > self.current_minute:
            self.current_minute = current_minute
            self.tokens_this_minute = 0
            self.requests_this_minute = 0

        # Remove token entries older than 2 minutes (keep some buffer)
        cutoff_time = time.time() - 120
        while self.usage_history and self.usage_history[0].timestamp < cutoff_time:
            self.usage_history.popleft()

        # Remove request entries older than 2 minutes
        while self.request_history and self.request_history[0] < cutoff_time:
            self.request_history.popleft()

    def _show_waiting_progress(self, seconds: int):
        """Show a progress bar for waiting."""
        try:
            import sys
            for i in range(seconds, 0, -1):
                sys.stdout.write(f"\r⏱️  Waiting {i}s... Press Ctrl+C to cancel")
                sys.stdout.flush()
                time.sleep(1)
            print("\r✅ Ready to continue!                     ")
        except KeyboardInterrupt:
            print("\n⏹️  Wait cancelled by user")
            raise

    def _show_thinking_progress(self, seconds: int):
        """Show thinking progress with animated spinner."""
        try:
            # Try to use Rich's animated status spinner
            from rich.status import Status
            from rich.console import Console

            console = Console()

            with console.status(f"[cyan]⏳ Waiting for API... ({seconds}s)[/cyan]", spinner="dots") as status:
                for i in range(seconds, 0, -1):
                    status.update(f"[cyan]⏳ Waiting for API... ({i}s)[/cyan]")
                    time.sleep(1)

        except ImportError:
            # Fallback to simple animation if Rich is not available
            import sys
            thinking_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            char_index = 0

            for i in range(seconds, 0, -1):
                char = thinking_chars[char_index % len(thinking_chars)]
                sys.stdout.write(f"\r{char} Waiting... ({i}s)")
                sys.stdout.flush()
                time.sleep(1)
                char_index += 1

            print("\r" + " " * 50 + "\r", end="", flush=True)

        except KeyboardInterrupt:
            print("\n⏹️  Cancelled")
            raise

    def smart_delay(self, estimated_tokens: int) -> bool:
        """
        Smart delay that shows natural thinking behavior instead of technical messages.

        Returns True if delayed, False if no delay needed.
        """
        if self.can_make_request(estimated_tokens):
            return False

        # Calculate wait time
        current_time = time.time()
        next_minute = (int(current_time // 60) + 1) * 60
        wait_seconds = max(1, int(next_minute - current_time))

        try:
            # Use Rich animated spinner for waiting
            from rich.status import Status
            from rich.console import Console

            console = Console()

            with console.status(f"[yellow]⏳ Rate limit reached. Waiting {wait_seconds}s...[/yellow]", spinner="dots") as status:
                for i in range(wait_seconds, 0, -1):
                    status.update(f"[yellow]⏳ Rate limit reached. Waiting {i}s...[/yellow]")
                    time.sleep(1)

            # Reset counter for new minute
            with self.lock:
                self.tokens_this_minute = 0
                self.requests_this_minute = 0

        except ImportError:
            # Fallback if Rich is not available
            import sys
            thinking_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            char_index = 0

            for i in range(wait_seconds, 0, -1):
                char = thinking_chars[char_index % len(thinking_chars)]
                sys.stdout.write(f"\r{char} Waiting... ({i}s)")
                sys.stdout.flush()
                time.sleep(1)
                char_index += 1

            print("\r" + " " * 30 + "\r", end="", flush=True)

            with self.lock:
                self.tokens_this_minute = 0
                self.requests_this_minute = 0

        except KeyboardInterrupt:
            print("\n⏹️  Cancelled")
            raise

        return True


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(model_name: str = "llama-3.3-70b-versatile", tier: str = "free", provider: str = "groq") -> RateLimiter:
    """Get or create global rate limiter instance.

    Args:
        model_name: Name of the model (used only if creating new instance)
        tier: "free" or "paid" tier (used only if creating new instance)
        provider: Provider name (groq, openrouter, etc.)

    Returns:
        Global RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(model_name=model_name, tier=tier, provider=provider)
    return _rate_limiter


def update_rate_limiter_model(model_name: str, tier: str = "free", provider: str = None):
    """Update the global rate limiter for a new model.

    Args:
        model_name: New model name
        tier: "free" or "paid" tier
        provider: Provider name (groq, openrouter, etc.)
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(model_name=model_name, tier=tier, provider=provider or "groq")
    else:
        _rate_limiter.update_model(model_name, tier, provider)


def set_rate_limiter(model_name: str = "llama-3.3-70b-versatile", tier: str = "free", provider: str = "groq"):
    """Configure the global rate limiter.

    Args:
        model_name: Name of the model
        tier: "free" or "paid" tier
        provider: Provider name (groq, openrouter, etc.)

    Returns:
        Configured RateLimiter instance
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(model_name=model_name, tier=tier, provider=provider)
    return _rate_limiter