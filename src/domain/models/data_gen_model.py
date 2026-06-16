from pydantic import BaseModel, Field
from typing import List
from src.domain.enums.campaign_basics import CampaignGoal,PromotingItem,CampaignNiche
from src.domain.enums.video_preferences import VideoType,VideoDuration,VideoOrientation

class CampaignBasicsModel(BaseModel):
    campaign_goal: CampaignGoal
    promoting_item: PromotingItem
    campaign_niches: List[CampaignNiche] = Field(default_factory=list, max_length=3, description="Up to 3 campaign niches")
    campaign_end_date: str
    campaign_description: str
    usage_ownership_rights: str
    video_sharing_preferences: str


class VideoPreferenceModel(BaseModel):
    video_orientation: VideoOrientation
    video_duration: VideoDuration
    video_type: VideoType = Field(description="A single video type enum")
    video_script: str = Field(..., description="A high-level rough idea for the video script. Provide a general concept and flow, without getting into specific scenes, timestamps, or exact dialogue.")

class FinalGenerationModel(BaseModel):
    campaign_basics: CampaignBasicsModel
    video_preferences: VideoPreferenceModel