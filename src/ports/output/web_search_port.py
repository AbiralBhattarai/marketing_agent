from abc import ABC, abstractmethod

class WebSearchPort(ABC):
    @abstractmethod
    async def search_web(self,query:str):
        pass