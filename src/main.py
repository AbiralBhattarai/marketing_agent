import asyncio
import sys
import os
import warnings
import logging
from typing import Dict,Any

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Suppress LangGraph MessagePack warning
warnings.filterwarnings("ignore", message=".*Deserializing unregistered type.*")

# Fix Windows terminal encoding issues
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from typing import Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import RetryPolicy

from src.domain.models.state import CampaignAgentState
from src.domain.models.context_fetch_model import SearchWebsites
from src.application.services.my_agent import (
    top_k_website_node,
    llm_node,
    execute_tools_node,
    infer_steps_node,
    human_verify_steps_node,
    gen_mermaid_diagram_node,
)

async def human_verify_websites_node(state: CampaignAgentState) -> Dict[str, Any]:
    """Interrupt point for human verification."""
    return {"websites_verified": True}

def react_router(state: CampaignAgentState) -> Literal["execute_tools_node", "__end__"]:
    if not state.messages:
        return END

    last_message = state.messages[-1]
    
    # If the LLM didn't call any tools, we are done
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return END
        
    # Otherwise, execute the tools
    return "execute_tools_node"

def execute_router(state: CampaignAgentState) -> Literal["llm_node", "__end__"]:
    if not state.messages:
        return "llm_node"
        
    last_message = state.messages[-1]
    content = str(last_message.content) if hasattr(last_message, 'content') else ""
        
    # If we just generated the final data, break the loop
    if "Final generation successful" in content:
        return END
        
    # Otherwise loop back to LLM for next decision
    return "llm_node"

def verify_steps_router(state: CampaignAgentState) -> Literal["gen_mermaid_diagram_node", "infer_steps_node"]:
    if state.steps_approved:
        return "gen_mermaid_diagram_node"
    return "infer_steps_node"

def build_hybrid_react_graph():
    retry_policy = RetryPolicy(max_attempts=3)

    workflow = StateGraph(CampaignAgentState)
    
    # Add nodes
    workflow.add_node("infer_steps_node", infer_steps_node, retry=retry_policy)
    workflow.add_node("human_verify_steps_node", human_verify_steps_node, retry=retry_policy)
    workflow.add_node("top_k_website_node", top_k_website_node, retry=retry_policy)
    workflow.add_node("human_verify_websites_node", human_verify_websites_node, retry=retry_policy)
    workflow.add_node("llm_node", llm_node, retry=retry_policy)
    workflow.add_node("execute_tools_node", execute_tools_node, retry=retry_policy)
    workflow.add_node("gen_mermaid_diagram_node", gen_mermaid_diagram_node, retry=retry_policy)
    
    # Linear Sequence Upfront
    workflow.set_entry_point("infer_steps_node")
    workflow.add_edge("infer_steps_node", "human_verify_steps_node")
    
    workflow.add_conditional_edges("human_verify_steps_node", verify_steps_router, {
        "gen_mermaid_diagram_node": "gen_mermaid_diagram_node",
        "infer_steps_node": "infer_steps_node"
    })
    
    workflow.add_edge("gen_mermaid_diagram_node", "top_k_website_node")
    workflow.add_edge("top_k_website_node", "human_verify_websites_node")
    workflow.add_edge("human_verify_websites_node", "llm_node")
    
    # ReAct Loop
    workflow.add_conditional_edges("llm_node", react_router, {
        "execute_tools_node": "execute_tools_node",
        END: END
    })
    
    workflow.add_conditional_edges("execute_tools_node", execute_router, {
        "llm_node": "llm_node",
        END: END
    })
    
    memory = MemorySaver()
    # Interrupt before the human verification dummy nodes
    return workflow.compile(checkpointer=memory, interrupt_before=["human_verify_steps_node", "human_verify_websites_node"])

async def handle_step_verification(graph, config, state):
    print("\n--- Interrupt: Manual Human Verification of Steps ---")
    choice = await asyncio.to_thread(input, "\nDo you approve these inferred campaign steps? (yes/no): ")
    if choice.lower().startswith('y'):
        logger.info("Steps approved by human.")
        graph.update_state(config, {"steps_approved": True})
    else:
        new_prompt = await asyncio.to_thread(input, "\nEnter your new campaign idea: ")
        logger.info(f"Steps rejected. New prompt: {new_prompt}")
        graph.update_state(config, {"user_prompt": new_prompt, "steps_approved": False})

async def handle_website_verification(graph, config, state):
    print("\n--- Interrupt: Manual Human Verification of Websites ---")
    top_k = state.values.get("top_k_websites")
    selected = []
    if top_k and hasattr(top_k, 'websites') and top_k.websites:
        print("\nWebsites Found:")
        for i, w in enumerate(top_k.websites):
            print(f"[{i}] {w.url}")
        choice = await asyncio.to_thread(input, "\nEnter the indices of the websites to select (e.g. 0, 2) or press Enter to skip: ")
        if choice.strip():
            try:
                indices = [int(x.strip()) for x in choice.split(',')]
                selected = [top_k.websites[idx] for idx in indices]
            except ValueError:
                logger.error("Invalid indices entered. Proceeding with empty selection.")
    
    logger.info(f"Human selected {len(selected)} websites.")
    graph.update_state(config, {"selected_websites": selected, "websites_verified": True})

async def run_workflow():
    logger.info("Compiling Hybrid ReAct Graph...")
    graph = build_hybrid_react_graph()
    
    try:
        png_data = graph.get_graph().draw_mermaid_png()
        with open("hybrid_react_graph.png", "wb") as f:
            f.write(png_data)
        logger.info("Graph saved as hybrid_react_graph.png")
    except Exception as e:
        logger.warning(f"Could not draw/save graph: {e}")

    config = {"configurable": {"thread_id": "hybrid-demo-1"}}
    
    # We must provide the required CampaignPlan placeholder (can be empty)
    from src.domain.models.input import CampaignPlan
    initial_state = CampaignAgentState(
        user_prompt="Im from FIFA. The worldcup is currently going on. I want to promote the worldcup official merchandise. Generate me the campaign.",
        campaign_plan=CampaignPlan(steps=[]),
        mermaid_diagram=""
    )

    print("\n--- Starting Hybrid Graph Execution ---")
    
    while True:
        try:
            async for event in graph.astream(initial_state if not graph.get_state(config).tasks else None, config=config):
                for key, value in event.items():
                    logger.debug(f"[Node Completed]: {key}")
                    if key == "infer_steps_node" and isinstance(value, dict) and "campaign_plan" in value:
                        v = value["campaign_plan"]
                        if hasattr(v, "steps"):
                            print(f"\n--- Inferred Campaign Steps ---")
                            for step in v.steps:
                                print(f"Step {step.step_id}: {step.task_name}")
                                print(f"  Description: {step.task_description}")
                                print(f"  Dependencies: {step.dependencies}")
                                print(f"  Parallel: {step.is_parallel}")
                            print("-------------------------------\n")
        except BaseException as e:
            logger.error(f"Paused/Error: {e}")
            
        state = graph.get_state(config)
        next_node = state.next
        
        if not next_node:
            break
            
        if "human_verify_steps_node" in next_node:
            await handle_step_verification(graph, config, state)
                
        elif "human_verify_websites_node" in next_node:
            await handle_website_verification(graph, config, state)

    print("\n--- Final Generated State ---")
    state = graph.get_state(config)
    
    basics = state.values.get("campaign_basics")
    if basics:
        print("\n--- Campaign Basics ---")
        goal_val = basics.campaign_goal.value if hasattr(basics.campaign_goal, 'value') else basics.campaign_goal
        print(f"🎯 Goal: {goal_val}")
        
        item_val = basics.promoting_item.value if hasattr(basics.promoting_item, 'value') else basics.promoting_item
        print(f"📦 Promoting Item: {item_val}")
        
        niches = [n.value if hasattr(n, 'value') else n for n in basics.campaign_niches]
        print(f"🏷️ Niches: {', '.join(niches)}")
        print(f"📝 Description: {basics.campaign_description}")
        
    prefs = state.values.get("video_preferences")
    if prefs:
        print("\n--- Video Preferences ---")
        orientation = prefs.video_orientation.value if hasattr(prefs.video_orientation, 'value') else prefs.video_orientation
        duration = prefs.video_duration.value if hasattr(prefs.video_duration, 'value') else prefs.video_duration
        vtype = prefs.video_type.value if hasattr(prefs.video_type, 'value') else prefs.video_type
        
        print(f"📱 Orientation: {orientation}")
        print(f"⏱️ Duration: {duration}")
        print(f"🎬 Type: {vtype}")
        print(f"📜 Script:\n{prefs.video_script}")
        
    diagram = state.values.get("mermaid_diagram")
    if diagram:
        print("\n--- Architecture Diagram ---")
        print("Mermaid Diagram generated successfully! Here is the code:")
        print(diagram)

if __name__ == "__main__":
    asyncio.run(run_workflow())
