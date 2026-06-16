from typing import List

from pydantic import BaseModel, Field

class SearchWebsites(BaseModel):
    title: str = Field(...,description="Title")
    url: str = Field(...,description="URL")
    headings:str = Field(...,description="Headings")
    description: str = Field(...,description="Description")



class HistoricalCampaignDataModel(BaseModel):
    campaign_title: str = Field(...,description="The exact name or title of the historical marketing campaign.")
    campaign_details: str = Field(...,description="A detailed breakdown of the campaign's strategy, channels used, and outcomes.")


class CurrentMarketingTrendsModel(BaseModel):
    title: str = Field(...,description="A short, catchy title summarizing the marketing trend.")
    description: str = Field(...,description="An explanation of why this trend is currently effective in the market.")


class TopMarketingTrends(BaseModel):
    trends: List[CurrentMarketingTrendsModel] = Field(..., description="A list of current marketing trends extracted from the text.")


class ExtractedCampaigns(BaseModel):
    campaigns: List[HistoricalCampaignDataModel] = Field(..., description="A list of historical campaigns relevant to the user's prompt.")


class TopKWebsites(BaseModel):
    websites: List[SearchWebsites] = Field(...,description="Websites")


class AggregatedContextModel(BaseModel):
    context_id: str = Field(...,description="Context ID")
    context: str= Field(...,description="Context")


