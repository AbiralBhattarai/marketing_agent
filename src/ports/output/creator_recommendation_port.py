from abc import ABC, abstractmethod

class CreatorRecommendationPort(ABC):
    @abstractmethod
    async def get_creator_recommendation(self):
       pass