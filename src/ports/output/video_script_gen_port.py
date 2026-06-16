from abc import ABC, abstractmethod

class VideoScriptGenPort(ABC):
    @abstractmethod
    async def generate_video_description(self):
        pass


