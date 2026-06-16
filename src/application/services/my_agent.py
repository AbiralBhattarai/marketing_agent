import asyncio
import logging
from typing import Dict, Any, List

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
from pydantic import BaseModel
from src.domain.models.input import SearchResultsFromQuery, AgentInput, CampaignPlan
from src.domain.models.context_fetch_model import HistoricalCampaignDataModel,SearchWebsites,TopKWebsites,CurrentMarketingTrendsModel, AggregatedContextModel, TopMarketingTrends, ExtractedCampaigns
from src.domain.models.data_gen_model import CampaignBasicsModel, VideoPreferenceModel, FinalGenerationModel
from src.domain.models.node_status_model import NodeStatusModel
from src.domain.models.state import CampaignAgentState
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from tenacity import retry, stop_after_attempt

from src.adapters.open_ai_adapter import AsyncOpenAIApiAdapter
from src.adapters.bs4_scraper_adapter import Bs4Scraper
from src.adapters.tavily_search_adapter import TavilySearchAdapter
from src.adapters.campaign_description_gen_adapter import CampaignDescriptionGenerationAdapter
from src.adapters.video_description_gen_adapter import VideoScriptGenAdapter
from src.adapters.creator_recommendation_adapter import CreatorRecommendationAdapter

from src.application.services.tools import build_top_k_web_search_tool,build_current_trend_search_tool,build_similar_campaign_search_tool, build_generation_tool

from src.application.services.llm import get_llm

# --- Global Dependency Initialization ---
_search_adapter = TavilySearchAdapter()
GLOBAL_TOOLS = [
    build_current_trend_search_tool(_search_adapter),
    build_similar_campaign_search_tool(_search_adapter),
    build_generation_tool()
]

# Quick lookup dictionary for execute_tools_node
GLOBAL_TOOLS_MAP = {tool.name: tool for tool in GLOBAL_TOOLS}


async def infer_steps_node(state: CampaignAgentState) -> Dict[str, Any]:
    logger.info("Starting infer_steps_node")
    llm = await get_llm()
    if state.user_prompt:
        system_prompt = f"""
        You are an expert Chief Marketing Officer (CMO). 
        Based on your expertise, your goal is to architect a comprehensive, step-by-step execution plan to launch this marketing campaign from scratch.
        Guidelines for your plan:
        1. Break the campaign down into logical, actionable steps (e.g., Market Research, Content Creation, Ad Deployment, Analytics Review).
        2. Think critically about dependencies: If a step requires the output of a previous step, you MUST include that previous step's ID in the `dependencies` array.
        3. Identify parallelization: If a step can be worked on simultaneously by a different team without blocking the critical path, flag it as `is_parallel=True`.
        4. Ensure the plan covers only the pre campaign launch parts. No post campaign analytics and things like that.
        NOTE: Make sure the plan falls in the context of this agent. This agent retrieves context about similar marketing campaigns and current marketing trends then uses those to generate required data.
        """
    else:
        logger.warning("No user prompt found in state.")
        return {"campaign_plan": CampaignPlan(steps=[])}

    res = await llm.structured_response(
        user_input=state.user_prompt,
        instructions=system_prompt,
        schema_model=CampaignPlan,
        temperature=0.0
    )
    logger.info("Successfully inferred campaign steps.")
    return {"campaign_plan": res}

async def human_verify_steps_node(state: CampaignAgentState) -> CampaignAgentState:
    """This is a dummy node to act as an interruption point for human verification of the steps."""
    logger.info("Hit human_verify_steps_node breakpoint.")
    return state

async def gen_mermaid_diagram_node(state: CampaignAgentState) -> Dict[str, Any]:
    """This node displays the mermaid diagram of the steps inferred in the infer_steps_node function"""
    logger.info("Generating Mermaid Diagram.")
    llm = await get_llm()
    instructions = "Draw a mermaid diagram based on the supplied campaign plan. Return ONLY the valid mermaid code block."

    if state.campaign_plan:
        # 1. Convert the Pydantic model to a string
        plan_string = state.campaign_plan.model_dump_json()

        # 2. Fix the "instructions" parameter
        res = await llm.response(
            user_input=plan_string,
            instructions=instructions
        )

        # 3. Grab just the string content from the AIMessage!
        mermaid_code = res.content

        return {"mermaid_diagram": mermaid_code}

    logger.warning("No campaign plan found. Cannot generate diagram.")
    return {"mermaid_diagram": ""}

async def top_k_website_node(state: CampaignAgentState) -> Dict[str, Any]:
    """Extracts product and category, and searches for top websites."""
    logger.info("Starting top_k_website_node.")
    llm = await get_llm()
    search_adapter = _search_adapter
    
    extraction_instructions = "Extract the specific product/item and its broad category from the user prompt."
    extraction = await llm.structured_response(
        user_input=state.user_prompt,
        instructions=extraction_instructions,
        schema_model=SearchResultsFromQuery
    )
    
    product = extraction.item
    category = extraction.category
    
    top_k_tool = build_top_k_web_search_tool(search_adapter)
    res = await top_k_tool.ainvoke({"agent_input": product})
    
    top_websites = res if isinstance(res, TopKWebsites) else TopKWebsites(websites=[])
    
    return {
        "campaign_product": product,
        "campaign_category": category,
        "top_k_websites": top_websites
    }


async def llm_node(state: CampaignAgentState) -> Dict[str, Any]:
    """The central ReAct Brain. Decides which tools to call."""
    logger.info("Starting central ReAct LLM Node.")
    llm = await get_llm()
    tools = GLOBAL_TOOLS
    
    system_prompt = """
    You are an expert marketing research agent. 
    You have access to 3 tools: websearch_tool, similar_campaign_search_tool, generation_tool.
    
    The user has already verified the top competitor websites. Your job is to:
    1. Research current marketing trends for the category using `websearch_tool`.
    2. Research similar historical campaigns using `similar_campaign_search_tool`.
    3. Once you have gathered sufficient trends and campaigns, call `generation_tool` to submit the final structured campaign data.
    """
    
    # 3. Create the conversational context from the State (acting as our memory)
    system_context = f"{system_prompt}\n\nWebsites Verified By Human: {state.websites_verified}\n\nCurrent Knowledge State:\n"
    if state.websites_verified and state.selected_websites:
        system_context += f"Human-Selected Websites: {state.selected_websites}\n"
    elif state.top_k_websites:
        system_context += f"Top Websites: {state.top_k_websites}\n"
    if state.marketing_trends:
        system_context += f"Marketing Trends: {state.marketing_trends}\n"
    if state.historical_campaigns:
        system_context += f"Historical Campaigns: {state.historical_campaigns}\n"

    # Construct the messages to pass
    messages_to_pass = list(state.messages)
    if not messages_to_pass:
        messages_to_pass = [HumanMessage(content=f"User Prompt: {state.user_prompt}\n\nPlease start your analysis and call the necessary tools.")]

    # 4. Bind the tools and call the LLM
    response = await llm.response(
        user_input=messages_to_pass,
        instructions=system_context,
        tools=tools,
        tool_choice="auto"
    )

    # Return the AIMessage containing the tool calls to update the state.messages
    return {"messages": [response]}


async def execute_tools_node(state: CampaignAgentState) -> Dict[str, Any]:
    """The Hands: Executes the tools requested by the llm_node."""
    logger.info("Executing tools from LLM response.")
    # Get the last message (which is the AIMessage from the LLM)
    last_message = state.messages[-1]
    
    llm = await get_llm()
    state_updates = {"messages": []}
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            args = tool_call["args"]
            tool_call_id = tool_call["id"]
                
            if tool_name not in GLOBAL_TOOLS_MAP:
                logger.error(f"Tool {tool_name} not found in registry.")
                continue
                
            tool_instance = GLOBAL_TOOLS_MAP[tool_name]
                
            if tool_name == "websearch_tool":
                logger.info(f"Executing websearch_tool for trends.")
                try:
                    res = await tool_instance.ainvoke(args)
                    trends_structured = await llm.structured_response(
                        user_input=str(res) if res else "No trends found.",
                        instructions="Extract current marketing trends from the text.",
                        schema_model=TopMarketingTrends
                    )
                    
                    current_trends = state.marketing_trends or []
                    new_trends = trends_structured.trends if hasattr(trends_structured, 'trends') else []
                    state_updates["marketing_trends"] = current_trends + new_trends
                    state_updates["messages"].append(ToolMessage(content="Trends gathered and synthesized.", tool_call_id=tool_call_id))
                except Exception as e:
                    logger.error(f"Error extracting trends: {str(e)}")
                    state_updates["messages"].append(ToolMessage(content=f"Error extracting trends: {str(e)}", tool_call_id=tool_call_id))
                
            elif tool_name == "similar_campaign_search_tool":
                logger.info(f"Executing similar_campaign_search_tool.")
                try:
                    res = await tool_instance.ainvoke(args)
                    campaigns_structured = await llm.structured_response(
                        user_input=str(res) if res else "No campaigns found.",
                        instructions="Extract historical campaigns from the text.",
                        schema_model=ExtractedCampaigns
                    )
                    
                    current_campaigns = state.historical_campaigns or []
                    new_campaigns = campaigns_structured.campaigns if hasattr(campaigns_structured, 'campaigns') else []
                    state_updates["historical_campaigns"] = current_campaigns + new_campaigns
                    state_updates["messages"].append(ToolMessage(content="Campaigns gathered and synthesized.", tool_call_id=tool_call_id))
                except Exception as e:
                    logger.error(f"Error extracting campaigns: {str(e)}")
                    state_updates["messages"].append(ToolMessage(content=f"Error extracting campaigns: {str(e)}", tool_call_id=tool_call_id))
                
            elif tool_name == "generation_tool":
                logger.info(f"Executing generation_tool.")
                try:
                    state_updates["campaign_basics"] = CampaignBasicsModel(**args.get("campaign_basics", {}))
                    state_updates["video_preferences"] = VideoPreferenceModel(**args.get("video_preferences", {}))
                    state_updates["messages"].append(ToolMessage(content="Final generation successful. Mission complete.", tool_call_id=tool_call_id))
                except Exception as e:
                    logger.error(f"Validation Error in generation: {str(e)}")
                    state_updates["messages"].append(ToolMessage(content=f"Validation Error: {str(e)}", tool_call_id=tool_call_id))

    return state_updates

