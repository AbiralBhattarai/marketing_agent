import os
from typing import List, Dict, Any
from tavily import AsyncTavilyClient

from src.domain.models.context_fetch_model import TopKWebsites, SearchWebsites
from src.ports.output.web_search_port import WebSearchPort

class TavilySearchAdapter(WebSearchPort):
    """
    Production-grade async adapter implementing WebSearchPort using Tavily API.
    """

    def __init__(
            self,
            api_key: str | None = None,
            search_depth: str = "advanced",
            max_results: int = 5
    ):
        resolved_key = api_key or os.getenv("TAVILY_API_KEY")
        if not resolved_key:
            raise ValueError("Tavily API key must be provided or set via TAVILY_API_KEY.")

        self._client = AsyncTavilyClient(api_key=resolved_key)
        self.search_depth = search_depth
        self.max_results = max_results

    async def search_web(self, query: str) -> TopKWebsites:
        if not query or not query.strip():
            return TopKWebsites(websites=[])

        response = await self._client.search(
            query=query.strip(),
            search_depth=self.search_depth,
            max_results=self.max_results,
        )

        raw_results = response.get("results", [])

        websites = []
        for item in raw_results:
            if "url" in item:
                websites.append(SearchWebsites(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    headings="",
                    description=item.get("content", "")
                ))

        return TopKWebsites(websites=websites)

    async def search_context(self, query: str) -> str:
        if not query or not query.strip():
            return "No context found."

        response = await self._client.search(
            query=query.strip(),
            search_depth=self.search_depth,
            max_results=self.max_results,
        )

        raw_results = response.get("results", [])
        
        # Combine the results into a string format that the LLM can easily read
        context_string = ""
        for i, item in enumerate(raw_results):
            title = item.get("title", "No Title")
            content = item.get("content", "No Content")
            url = item.get("url", "No URL")
            context_string += f"Result {i+1}:\nTitle: {title}\nURL: {url}\nContent: {content}\n\n"

        return context_string
