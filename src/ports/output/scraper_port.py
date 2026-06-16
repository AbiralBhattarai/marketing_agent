from abc import ABC, abstractmethod

class ScraperPort(ABC):
    @abstractmethod
    async def scrape_brand_site(self, brand_site:str):
        pass