from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel

class LLMPort(ABC):
    @abstractmethod
    async def response(
            self,
            user_input: Union[str, List[Dict[str, str]]],
            instructions: str,
            model: str,
            temperature: float,
            tools: Optional[List[Dict[str, Any]]],
            tool_choice: str,
    ) -> Any:
        pass

    @abstractmethod
    async def structured_response(
            self,
            user_input: Union[str, List[Dict[str, str]]],
            instructions: str,
            schema_model: Type[BaseModel],
            model: str,
            temperature: float,
            tools: Optional[List[Dict[str, Any]]],
    ) -> Any:
        pass