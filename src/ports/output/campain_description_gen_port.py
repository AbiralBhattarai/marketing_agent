from abc import ABC, abstractmethod

class CampaignDescriptionGeneratorPort(ABC):
    @abstractmethod
    async def generate_campaign_description(self):
        pass