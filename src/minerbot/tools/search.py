"""Web search tool using Tavily"""

import os
from typing import Any, Callable, Literal


def get_search_tool() -> Callable[..., Any] | None:
    """Create web search tool using Tavily.
    
    Returns:
        Search function or None if TAVILY_API_KEY not set
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None
    
    from tavily import TavilyClient
    
    tavily_client = TavilyClient(api_key=api_key)
    
    def internet_search(
        query: str,
        max_results: int = 5,
        topic: Literal["general", "news", "finance"] = "general",
    ) -> str:
        """Run a web search."""
        results = tavily_client.search(
            query,
            max_results=max_results,
            topic=topic,
        )
        return str(results)
    
    return internet_search
