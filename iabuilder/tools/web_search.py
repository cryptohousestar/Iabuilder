"""Simple web search tool using DuckDuckGo."""

from typing import Any, Dict

from .base import Tool


class WebSearchTool(Tool):
    """Simple web search using duckduckgo-search library."""

    def _get_name(self) -> str:
        return "web_search"

    def _get_description(self) -> str:
        return "Search the web for information. Returns relevant results from DuckDuckGo."

    def _get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Execute web search.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            Search results
        """
        try:
            # Try using ddgs library (formerly duckduckgo-search)
            from ddgs import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })

            if results:
                # Format results for display
                formatted = []
                for i, r in enumerate(results, 1):
                    formatted.append(f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet']}")

                return {
                    "success": True,
                    "result": "\n\n".join(formatted),
                    "results": results,
                    "count": len(results),
                }
            else:
                return {
                    "success": True,
                    "result": "No results found.",
                    "results": [],
                    "count": 0,
                }

        except ImportError:
            return {
                "success": False,
                "error": "ddgs not installed. Run: pip install ddgs",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
            }
