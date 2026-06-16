import json
from typing import TypedDict, Annotated, Literal
from pydantic import BaseModel
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from src.domain.models.state import CampaignAgentState
from src.domain.models.context_fetch_model import (
    SearchWebsites, TopKWebsites, HistoricalCampaignDataModel,
    CurrentMarketingTrendsModel, AggregatedContextModel
)
from src.domain.models.data_gen_model import CampaignBasicsModel, VideoPreferenceModel
from src.domain.models.node_status_model import NodeStatusModel

from src.ports.output.llm_port import LLMPort
from src.ports.output.web_search_port import WebSearchPort
from src.ports.output.campain_description_gen_port import CampaignDescriptionGeneratorPort
from src.ports.output.video_script_gen_port import VideoScriptGenPort
from src.ports.output.creator_recommendation_port import CreatorRecommendationPort
from src.ports.output.scraper_port import ScraperPort
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage

# --- Wrapper Models for Structured Output ---
class MarketingTrendsList(BaseModel):
    trends: list[CurrentMarketingTrendsModel]

class HistoricalCampaignsList(BaseModel):
    campaigns: list[HistoricalCampaignDataModel]


# --- Common Nodes (for both manual and agentic) ---

async def human_verify_websites_node(state: CampaignAgentState):
    # This node acts as an interrupt point. The state will be updated externally.
    return {"websites_verified": True}

async def human_verify_context_node(state: CampaignAgentState):
    # This node acts as an interrupt point.
    return {"context_verified": True}

def get_data_gen_node(llm_adapter: LLMPort):
    async def data_gen_node(state: CampaignAgentState):
        context = f"Prompt: {state.user_prompt}\n"
        if state.marketing_trends:
            context += f"Trends: {[t.title for t in state.marketing_trends]}\n"
        if state.historical_campaigns:
            context += f"Campaigns: {[c.campaign_title for c in state.historical_campaigns]}\n"

        # Generate Campaign Basics
        campaign_basics_structured = await llm_adapter.structured_response(
            user_input=context,
            instructions="Generate the campaign basics based on the gathered context.",
            schema_model=CampaignBasicsModel
        )
        
        campaign_basics = campaign_basics_structured if isinstance(campaign_basics_structured, CampaignBasicsModel) else None

        # Generate Video Preferences
        video_pref_structured = await llm_adapter.structured_response(
            user_input=context,
            instructions="Generate the video preferences and video script based on the gathered context.",
            schema_model=VideoPreferenceModel
        )
        
        vid_model = video_pref_structured if isinstance(video_pref_structured, VideoPreferenceModel) else None
        video_script = vid_model.video_script if vid_model and vid_model.video_script else "Generated video script..."

        return {
            "campaign_basics": campaign_basics,
            "video_preferences": vid_model,
            "campaign_description": campaign_basics.campaign_description if campaign_basics else "Fallback description",
            "video_script": video_script
        }
    return data_gen_node


# --- Manual Graph Builders ---

def get_manual_web_search_node(web_search_adapter: WebSearchPort):
    async def web_search_node(state: CampaignAgentState):
        query = state.user_prompt
        # Manually call web search port
        top_websites = await web_search_adapter.search_web(query)
        # Convert to TopKWebsites model if not already
        if not isinstance(top_websites, TopKWebsites):
            top_websites = TopKWebsites(websites=[])
        return {"top_k_websites": top_websites}
    return web_search_node

def get_manual_context_research_node(web_search_adapter: WebSearchPort, scraper_adapter: ScraperPort, llm_adapter: LLMPort):
    async def context_research_node(state: CampaignAgentState):
        # Manually perform searches
        trends_res = await web_search_adapter.search_web(f"current marketing trends for {state.user_prompt}")
        campaigns_res = await web_search_adapter.search_web(f"similar campaigns for {state.user_prompt}")
        
        # Manually scrape a website
        scrape_data = ""
        if state.selected_websites:
            for site in state.selected_websites:
                try:
                    data = await scraper_adapter.scrape_brand_site(site.url)
                    scrape_data += f"\nData from {site.url}: {data}\n"
                except Exception:
                    pass
        
        # Now use LLM to summarize and structure the results
        combined_text = f"Trends search results: {trends_res}\nCampaigns search results: {campaigns_res}\nScrape Data: {scrape_data}"
        
        trends_structured = await llm_adapter.structured_response(
            user_input=combined_text,
            instructions="Extract the marketing trends from the provided text.",
            schema_model=MarketingTrendsList
        )
        trends_list = trends_structured.trends if isinstance(trends_structured, MarketingTrendsList) else []

        campaigns_structured = await llm_adapter.structured_response(
            user_input=combined_text,
            instructions="Extract the historical/similar campaigns from the provided text.",
            schema_model=HistoricalCampaignsList
        )
        campaigns_list = campaigns_structured.campaigns if isinstance(campaigns_structured, HistoricalCampaignsList) else []
                
        return {
            "marketing_trends": trends_list,
            "historical_campaigns": campaigns_list
        }
    return context_research_node

def manual_router(state: CampaignAgentState):
    if not state.top_k_websites:
        return "web_search_node"
    if not state.websites_verified:
        return "human_verify_websites_node"
    if not state.marketing_trends and not state.historical_campaigns:
        return "context_research_node"
    if not state.context_verified:
        return "human_verify_context_node"
    return "data_gen_node"

def build_manual_graph(
    llm_adapter: LLMPort,
    web_search_adapter: WebSearchPort,
    scraper_adapter: ScraperPort,
    campaign_desc_adapter: CampaignDescriptionGeneratorPort,
    video_script_adapter: VideoScriptGenPort,
    creator_rec_adapter: CreatorRecommendationPort,
    checkpointer=None
):
    workflow = StateGraph(CampaignAgentState)
    
    workflow.add_node("web_search_node", get_manual_web_search_node(web_search_adapter))
    workflow.add_node("human_verify_websites_node", human_verify_websites_node)
    workflow.add_node("context_research_node", get_manual_context_research_node(web_search_adapter, scraper_adapter, llm_adapter))
    workflow.add_node("human_verify_context_node", human_verify_context_node)
    workflow.add_node("data_gen_node", get_data_gen_node(llm_adapter))
    
    path_map = [
        "web_search_node",
        "human_verify_websites_node",
        "context_research_node",
        "human_verify_context_node",
        "data_gen_node"
    ]
    workflow.set_conditional_entry_point(manual_router, path_map)
    workflow.add_conditional_edges("web_search_node", manual_router, path_map)
    workflow.add_conditional_edges("human_verify_websites_node", manual_router, path_map)
    workflow.add_conditional_edges("context_research_node", manual_router, path_map)
    workflow.add_conditional_edges("human_verify_context_node", manual_router, path_map)
    workflow.add_edge("data_gen_node", END)
    
    return workflow.compile(checkpointer=checkpointer, interrupt_before=["human_verify_websites_node", "human_verify_context_node"])


# --- Agentic Graph Builders ---

def get_agentic_web_search_node(llm_adapter: LLMPort, web_search_adapter: WebSearchPort):
    async def agentic_web_search_node(state: CampaignAgentState):
        tools = [{
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the web for top websites related to a query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"}
                    },
                    "required": ["query"]
                }
            }
        }]
        
        prompt = f"Find top websites for: {state.user_prompt}. Use the search_web tool."
        
        response = await llm_adapter.response(
            user_input=prompt,
            instructions="You are a marketing agent. Use tools to find info.",
            tools=tools,
            tool_choice="auto"
        )
        
        websites = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call["name"] == "search_web":
                    args = tool_call["args"]
                    search_res = await web_search_adapter.search_web(args["query"])
                    websites = search_res.websites if hasattr(search_res, 'websites') else []
        
        if not websites:
            websites = ["dummy1.com", "dummy2.com"] # Fallback dummy
            
        return {"top_k_websites": TopKWebsites(websites=websites)}
    return agentic_web_search_node

def get_agentic_context_research_node(llm_adapter: LLMPort, web_search_adapter: WebSearchPort, scraper_adapter: ScraperPort):
    async def agentic_context_research_node(state: CampaignAgentState):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_trends",
                    "description": "Search for current marketing trends",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_campaigns",
                    "description": "Search for similar campaigns",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scrape_site",
                    "description": "Scrape a website",
                    "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
                }
            }
        ]
        
        prompt = f"Find marketing trends and similar campaigns for: {state.user_prompt}. Scrape sites if necessary."
        
        response = await llm_adapter.response(
            user_input=prompt,
            instructions="You are a marketing agent. Use tools to gather trends and campaigns.",
            tools=tools,
            tool_choice="auto"
        )
        
        gathered_data = ""
        # Handle Langchain tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                args = tool_call["args"]
                if tool_call["name"] == "search_trends":
                    res = await web_search_adapter.search_web(args["query"])
                    gathered_data += f"\nTrends Search for {args['query']}: {res}"
                elif tool_call["name"] == "search_campaigns":
                    res = await web_search_adapter.search_web(args["query"])
                    gathered_data += f"\nCampaigns Search for {args['query']}: {res}"
                elif tool_call["name"] == "scrape_site":
                    try:
                        res = await scraper_adapter.scrape_brand_site(args["url"])
                        gathered_data += f"\nScrape data for {args['url']}: {res}"
                    except Exception:
                        gathered_data += f"\nFailed to scrape {args['url']}"
                        
        if not gathered_data:
            gathered_data = "No data gathered."

        # After tool usage, generate structured domain models
        trends_structured = await llm_adapter.structured_response(
            user_input=gathered_data,
            instructions="Extract the marketing trends from the provided text.",
            schema_model=MarketingTrendsList
        )
        
        trends_list = trends_structured.trends if isinstance(trends_structured, MarketingTrendsList) else [CurrentMarketingTrendsModel(title="Fallback Trend", description="Could not extract trends from LLM")]

        campaigns_structured = await llm_adapter.structured_response(
            user_input=gathered_data,
            instructions="Extract the historical/similar campaigns from the provided text.",
            schema_model=HistoricalCampaignsList
        )
        
        campaigns_list = campaigns_structured.campaigns if isinstance(campaigns_structured, HistoricalCampaignsList) else [HistoricalCampaignDataModel(
                campaign_title="Fallback Campaign",
                campaign_description="Could not extract campaigns from LLM",
                campaign_budget=0.0,
                campaign_roi=0.0,
                campaign_location="Global"
            )]
        
        return {
            "marketing_trends": trends_list,
            "historical_campaigns": campaigns_list
        }
    return agentic_context_research_node

def agentic_router(state: CampaignAgentState):
    if not state.top_k_websites:
        return "agentic_web_search_node"
    if not state.websites_verified:
        return "human_verify_websites_node"
    if not state.marketing_trends and not state.historical_campaigns:
        return "agentic_context_research_node"
    if not state.context_verified:
        return "human_verify_context_node"
    return "data_gen_node"


def build_agentic_graph(
    llm_adapter: LLMPort,
    web_search_adapter: WebSearchPort,
    scraper_adapter: ScraperPort,
    campaign_desc_adapter: CampaignDescriptionGeneratorPort,
    video_script_adapter: VideoScriptGenPort,
    creator_rec_adapter: CreatorRecommendationPort,
    checkpointer=None
):
    workflow = StateGraph(CampaignAgentState)
    
    workflow.add_node("agentic_web_search_node", get_agentic_web_search_node(llm_adapter, web_search_adapter))
    workflow.add_node("human_verify_websites_node", human_verify_websites_node)
    workflow.add_node("agentic_context_research_node", get_agentic_context_research_node(llm_adapter, web_search_adapter, scraper_adapter))
    workflow.add_node("human_verify_context_node", human_verify_context_node)
    workflow.add_node("data_gen_node", get_data_gen_node(llm_adapter))
    
    path_map = [
        "agentic_web_search_node",
        "human_verify_websites_node",
        "agentic_context_research_node",
        "human_verify_context_node",
        "data_gen_node"
    ]
    workflow.set_conditional_entry_point(agentic_router, path_map)
    workflow.add_conditional_edges("agentic_web_search_node", agentic_router, path_map)
    workflow.add_conditional_edges("human_verify_websites_node", agentic_router, path_map)
    workflow.add_conditional_edges("agentic_context_research_node", agentic_router, path_map)
    workflow.add_conditional_edges("human_verify_context_node", agentic_router, path_map)
    workflow.add_edge("data_gen_node", END)
    
    return workflow.compile(checkpointer=checkpointer, interrupt_before=["human_verify_websites_node", "human_verify_context_node"])
