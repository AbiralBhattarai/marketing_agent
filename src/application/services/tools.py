from langchain.tools import tool
from tenacity import retry, stop_after_attempt

from src.domain.models.context_fetch_model import TopKWebsites, SearchWebsites
from src.domain.models.input import AgentInput
from src.domain.models.data_gen_model import FinalGenerationModel


def build_top_k_web_search_tool(search_adapter):

    @tool(args_schema=AgentInput)
    @retry(stop=stop_after_attempt(3))
    async def search_tool(agent_input: str):
        """
        Search web for brand, competitors, campaigns, trends.
        """
        return await search_adapter.search_web(agent_input)

    return search_tool


#
# def build_scrape_tool(scraper):
#
#     @tool
#     async def scrape_tool(url: str):
#         """
#         Scrape a website and extract structured content.
#         """
#         return await scraper.scrape_brand_site(url)
#
#     return scrape_tool


def build_current_trend_search_tool(search_adapter):
    @tool(args_schema=AgentInput)
    @retry(stop=stop_after_attempt(3))
    async def websearch_tool(agent_input: str):
        """Search for top k websites based on search query."""
        return await search_adapter.search_web(agent_input)
    return websearch_tool


def build_similar_campaign_search_tool(search_adapter):
    @tool(args_schema=AgentInput)
    @retry(stop=stop_after_attempt(3))
    async def similar_campaign_search_tool(agent_input: str):
        """Search for top k campaigns based on search query."""
        return await search_adapter.search_web(agent_input)
    return similar_campaign_search_tool


def build_generation_tool():
    @tool(args_schema=FinalGenerationModel)
    @retry(stop=stop_after_attempt(3))
    async def generation_tool(*args, **kwargs):
        """
        Call this tool ONLY when you have gathered enough website context, marketing trends, and historical campaigns.
        This tool submits your final generated structured data for the campaign.
        """
        return kwargs
    return generation_tool

