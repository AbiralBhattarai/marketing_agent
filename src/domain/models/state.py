from pydantic import BaseModel, Field
from src.domain.models.db_model import BrandDataModel
from src.domain.models.context_fetch_model import SearchWebsites,HistoricalCampaignDataModel,CurrentMarketingTrendsModel,TopKWebsites,AggregatedContextModel
from src.domain.models.data_gen_model import CampaignBasicsModel,VideoPreferenceModel
from src.domain.models.input import CampaignPlan
from src.domain.models.node_status_model import NodeStatusModel

from langgraph.graph.message import add_messages
from typing import Annotated, Any

class CampaignAgentState(BaseModel):
    messages: Annotated[list[Any], add_messages] = Field(default_factory=list)
    user_prompt: str
    campaign_product: str | None = None
    campaign_category: str | None = None
    campaign_plan: CampaignPlan
    steps_approved: bool = False
    mermaid_diagram: str
    # brand_data: BrandDataModel | None = None
    top_k_websites: TopKWebsites | None = None
    selected_websites: list[SearchWebsites] = Field(default_factory=list)
    historical_campaigns: list[HistoricalCampaignDataModel] = Field(
        default_factory=list
    )
    marketing_trends: list[CurrentMarketingTrendsModel] = Field(
        default_factory=list
    )
    aggregated_context: AggregatedContextModel | None = None
    campaign_websites: list[SearchWebsites] = Field(default_factory=list)
    current_trend_websites : list[SearchWebsites] = Field(default_factory=list)
    websites_verified: bool = False
    context_verified: bool = False
    campaign_basics: CampaignBasicsModel | None = None
    video_preferences: VideoPreferenceModel | None = None
    # Outputs from downstream services
    node_statuses: dict[str, NodeStatusModel] = Field(default_factory=dict, description="Tracks the execution status and retries of each node.")