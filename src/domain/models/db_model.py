from pydantic import BaseModel, Field
from typing import List




class CampaignDataModel(BaseModel):
    brand_id: int = Field(...,description="Brand ID")
    campaign_name: str = Field(...,description="Campaign Name")
    campaign_id: int = Field(...,description="Campaign ID")
    campaign_description : str = Field(...,description="Campaign Description")
    budget: float = Field(...,description="Cost")
    success_rate: float = Field(...,description="Success Rate")
    failure_rate : float = Field(...,description="Failure Rate")
    roi: float = Field(...,description="ROI")



class BrandDataModel(BaseModel):
    brand_id: int = Field(..., description="Brand ID")
    brand_name: str = Field(...,description="Brand Name")
    brand_description: str = Field(...,description="Brand Description")
    brand_industry: str = Field(...,description="Brand Industry")
    brand_website: str = Field(...,description="Brand Website")
    past_campaigns: List[CampaignDataModel]
