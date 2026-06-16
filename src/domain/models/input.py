from pydantic import BaseModel, Field
from langchain.messages import HumanMessage,AIMessage
from typing import List

class AgentInput(BaseModel):
    agent_input : str = Field(...,description="User Input")

class SearchResultsFromQuery(BaseModel):
    item: str
    category: str

class UserInput(BaseModel):
    user_input: HumanMessage = Field(...,description="LLM Message")


class CampaignStep(BaseModel):
    step_id: int = Field(
        ...,
        description="The unique integer ID of this step (e.g., 1, 2, 3)."
    )
    task_name: str = Field(
        ...,
        description="A clear, concise name for the task to be executed."
    )
    task_description: str = Field(
        ...,
        description="A detailed description of what needs to be done in this step."
    )
    dependencies: List[int] = Field(
        default_factory=list,
        description="A list of step_ids that MUST be completed before this task can start. Leave empty if none."
    )
    is_parallel: bool = Field(
        default=False,
        description="Set to True if this task can be executed at the same time as other tasks."
    )
# THIS is the model you actually pass to the LLM!
class CampaignPlan(BaseModel):
    steps: List[CampaignStep] = Field(
        ...,
        description="The full list of sequential and parallel steps required to launch the campaign."
    )