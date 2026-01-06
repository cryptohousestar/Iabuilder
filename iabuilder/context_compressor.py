"""Context compression system for long conversations."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

# Try to import tiktoken, but have fallback if not available
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

if TYPE_CHECKING:
    from .conversation import Conversation


class ContextCompressor:
    """Intelligent context compression for long conversations."""

    def __init__(self, max_tokens: int = 150000, compression_threshold: int = 50000):
        """Initialize context compressor.

        Args:
            max_tokens: Maximum tokens to keep in active context
            compression_threshold: Token count that triggers compression
        """
        self.max_tokens = max_tokens
        self.compression_threshold = compression_threshold
        self.tokenizer = None

        # Only initialize tokenizer if tiktoken is available
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
            except Exception:
                pass

        # Compression directories
        self.resume_dir = Path.home() / ".iabuilder" / "resume"
        self.resume_dir.mkdir(parents=True, exist_ok=True)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                pass

        # Fallback approximation: ~4 chars per token
        return len(text) // 4

    def estimate_conversation_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate total tokens in conversation."""
        # If tiktoken is not available, use a simple approximation
        if not TIKTOKEN_AVAILABLE:
            total_chars = 0
            for msg in messages:
                content = msg.get("content", "")
                if content:
                    total_chars += len(content)

                # Add approximate size for tool calls
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    for tc in tool_calls:
                        if isinstance(tc, str):
                            total_chars += len(tc)
                        elif isinstance(tc, dict):
                            func_args = tc.get("function", {}).get("arguments", "")
                            total_chars += len(func_args) + 50
                        elif hasattr(tc, 'function'):
                            func_args = getattr(getattr(tc, 'function', None), 'arguments', '')
                            total_chars += len(func_args) + 50

            return total_chars // 4  # Rough approximation: 4 chars per token

        # Use tiktoken if available
        total_tokens = 0
        for msg in messages:
            # Count content
            content = msg.get("content", "")
            if content:
                total_tokens += self.count_tokens(content)

            # Count tool calls
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    # Handle different tool call formats (dict, string, or object)
                    if isinstance(tc, str):
                        total_tokens += self.count_tokens(tc)
                    elif isinstance(tc, dict):
                        func_name = tc.get("function", {}).get("name", "")
                        func_args = tc.get("function", {}).get("arguments", "")
                        total_tokens += self.count_tokens(f"{func_name}({func_args})")
                    elif hasattr(tc, 'function'):
                        # Object with function attribute
                        func = getattr(tc, 'function', None)
                        if func:
                            func_name = getattr(func, 'name', '')
                            func_args = getattr(func, 'arguments', '')
                            total_tokens += self.count_tokens(f"{func_name}({func_args})")

        return total_tokens

    def should_compress(self, conversation) -> bool:
        """Check if conversation needs compression."""
        token_count = self.estimate_conversation_tokens(conversation.messages)
        return token_count > self.compression_threshold

    def compress_conversation(self, conversation) -> Dict[str, Any]:
        """Compress conversation intelligently.

        Returns:
            Dictionary with compression results
        """
        print("🗜️  Compressing conversation context...")

        # Analyze conversation
        analysis = self._analyze_conversation(conversation.messages)

        # Create compression summary
        compression = self._create_compression_summary(
            analysis, conversation.session_id
        )

        # Save compressed version
        self._save_compressed_version(compression, conversation.session_id)

        # Create new truncated conversation
        truncated_messages = self._create_truncated_messages(
            conversation.messages, analysis
        )

        print("✅ Context compression completed!")
        print(
            f"   📊 Reduced from {analysis['total_tokens']} to {len(truncated_messages)} messages"
        )
        print(
            f"   💾 Compressed version saved to resume/{conversation.session_id}.json"
        )

        return {
            "compressed": True,
            "original_tokens": analysis["total_tokens"],
            "compressed_messages": len(truncated_messages),
            "summary": compression,
            "truncated_messages": truncated_messages,
        }

    def _analyze_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze conversation for compression."""
        analysis = {
            "total_messages": len(messages),
            "total_tokens": self.estimate_conversation_tokens(messages),
            "tool_calls": [],
            "file_operations": [],
            "important_decisions": [],
            "code_changes": [],
            "recent_messages": [],
        }

        # Add warning if tiktoken is not available
        if not TIKTOKEN_AVAILABLE:
            print("⚠️ Warning: tiktoken not available, using approximate token counting")

        # Extract important information
        for i, msg in enumerate(messages):
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Track tool calls
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    func_name = ""
                    func_args = ""
                    if isinstance(tc, str):
                        func_name = tc
                    elif isinstance(tc, dict):
                        func_name = tc.get("function", {}).get("name", "")
                        func_args = tc.get("function", {}).get("arguments", "")
                    elif hasattr(tc, 'function'):
                        func = getattr(tc, 'function', None)
                        if func:
                            func_name = getattr(func, 'name', '')
                            func_args = getattr(func, 'arguments', '')

                    if func_name:
                        analysis["tool_calls"].append(
                            {"function": func_name, "args": func_args, "message_index": i}
                        )

                # Track file operations
                if func_name in ["read_file", "write_file", "edit_file"]:
                    try:
                        args = json.loads(func_args)
                        file_path = args.get("file_path", "")
                        if file_path:
                            analysis["file_operations"].append(
                                {
                                    "operation": func_name,
                                    "file": file_path,
                                    "message_index": i,
                                }
                            )
                    except:
                        pass

            # Track recent messages (last 20)
            if i >= len(messages) - 20:
                analysis["recent_messages"].append(msg)

            # Extract important content
            if role == "assistant" and content:
                # Look for important patterns
                if any(
                    keyword in content.lower()
                    for keyword in [
                        "completed",
                        "finished",
                        "done",
                        "created",
                        "modified",
                        "changed",
                        "updated",
                        "fixed",
                        "implemented",
                    ]
                ):
                    analysis["important_decisions"].append(
                        {"content": content[:200], "message_index": i}
                    )

        return analysis

    def _create_compression_summary(
        self, analysis: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """Create a summary of the compressed conversation."""
        summary = {
            "session_id": session_id,
            "compressed_at": datetime.now().isoformat(),
            "original_stats": {
                "total_messages": analysis["total_messages"],
                "total_tokens": analysis["total_tokens"],
            },
            "file_operations": analysis["file_operations"],
            "tool_usage": {
                "total_tool_calls": len(analysis["tool_calls"]),
                "tools_used": list(
                    set(tc["function"] for tc in analysis["tool_calls"])
                ),
            },
            "important_decisions": analysis["important_decisions"][
                -10:
            ],  # Last 10 important decisions
            "key_files": list(set(op["file"] for op in analysis["file_operations"]))[
                :20
            ],  # Top 20 files
            "summary_text": self._generate_summary_text(analysis),
        }

        return summary

    def _generate_summary_text(self, analysis: Dict[str, Any]) -> str:
        """Generate human-readable summary text."""
        lines = []

        # Basic stats
        lines.append(
            f"This conversation had {analysis['total_messages']} messages and used approximately {analysis['total_tokens']} tokens."
        )

        # Tool usage
        if analysis["tool_calls"]:
            tool_counts = {}
            for tc in analysis["tool_calls"]:
                tool_counts[tc["function"]] = tool_counts.get(tc["function"], 0) + 1

            lines.append(
                f"Used {len(analysis['tool_calls'])} tools: "
                + ", ".join(f"{tool} ({count}x)" for tool, count in tool_counts.items())
            )

        # File operations
        if analysis["file_operations"]:
            file_counts = {}
            for op in analysis["file_operations"]:
                file_counts[op["file"]] = file_counts.get(op["file"], 0) + 1

            top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[
                :5
            ]
            lines.append(
                f"Worked with {len(file_counts)} files, top files: "
                + ", ".join(f"{file} ({count}x)" for file, count in top_files)
            )

        # Important decisions
        if analysis["important_decisions"]:
            lines.append(
                f"Made {len(analysis['important_decisions'])} important decisions/completions."
            )

        return " ".join(lines)

    def _create_truncated_messages(
        self, messages: List[Dict[str, Any]], analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create truncated message list for continued conversation."""
        # Keep recent messages
        recent_count = 20
        truncated = (
            messages[-recent_count:] if len(messages) > recent_count else messages
        )

        # Add compression summary as system message
        summary_text = self._generate_summary_text(analysis)

        compression_message = {
            "role": "system",
            "content": f"CONTEXT COMPRESSED: {summary_text}\n\nThis conversation has been compressed to save tokens. Key information from previous messages is summarized above.",
            "timestamp": datetime.now().isoformat(),
            "compression": True,
        }

        # Insert at the beginning if we truncated
        if len(messages) > recent_count:
            truncated.insert(0, compression_message)

        return truncated

    def _save_compressed_version(self, compression: Dict[str, Any], session_id: str):
        """Save compressed conversation to resume directory."""
        filename = f"{session_id}_compressed.json"
        filepath = self.resume_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(compression, f, indent=2, ensure_ascii=False)

    def load_compressed_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a compressed conversation."""
        filename = f"{session_id}_compressed.json"
        filepath = self.resume_dir / filename

        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_compressed_sessions(self) -> List[Dict[str, Any]]:
        """List all compressed conversation sessions."""
        sessions = []
        for file_path in self.resume_dir.glob("*_compressed.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["file_path"] = file_path
                    sessions.append(data)
            except Exception as e:
                print(f"Error loading compressed session {file_path}: {e}")

        return sorted(sessions, key=lambda x: x.get("compressed_at", ""), reverse=True)
