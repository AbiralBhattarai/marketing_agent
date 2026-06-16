import logging
import os
from typing import Any, Dict, List, Optional, Type, Union
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from pydantic import BaseModel
from src.ports.output.llm_port import LLMPort

load_dotenv()

logger = logging.getLogger(__name__)


class ResponseConfig:
    """
    Configuration for response generation.
    """

    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_TEMPERATURE = 0.0
    TOOL_CHOICE_AUTO = "auto"
    TOOL_CHOICE_REQUIRED = "required"
    MODELS_WITHOUT_TEMPERATURE = ["gpt-5", "gpt-5-mini"]


class AsyncOpenAIApiAdapter(LLMPort):
    """
    A wrapper class for OpenAI's AsyncClient that simplifies making API calls.
    """

    def __init__(self):
        self.openai_api_key = os.getenv(
            "OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", None)
        )

        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API Key must be provided via environment variables or .env file"
            )

    async def response(
        self,
        user_input: Union[str, List[Dict[str, str]]],
        instructions: str,
        model: str = ResponseConfig.DEFAULT_MODEL,
        temperature: float = ResponseConfig.DEFAULT_TEMPERATURE,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = ResponseConfig.TOOL_CHOICE_AUTO,
    ) -> Any:
        if not 0.0 <= temperature <= 1.0:
            raise ValueError(
                f"Temperature must be between 0.0 and 1.0, got {temperature}"
            )

        messages = []
        if instructions:
            messages.append(SystemMessage(content=instructions))
            
        if isinstance(user_input, list):
            # Check if it's already a list of Langchain BaseMessages
            if len(user_input) > 0 and isinstance(user_input[0], BaseMessage):
                messages.extend(user_input)
            else:
                # Assuming user_input is a list of dicts like [{"role": "user", "content": "..."}]
                for msg in user_input:
                    if msg.get("role") == "system":
                        messages.append(SystemMessage(content=msg.get("content", "")))
                    else:
                        messages.append(HumanMessage(content=msg.get("content", "")))
        elif isinstance(user_input, str):
            messages.append(HumanMessage(content=user_input))

        llm = ChatOpenAI(
            model=model,
            temperature=temperature if model not in ResponseConfig.MODELS_WITHOUT_TEMPERATURE else None,
            api_key=self.openai_api_key
        )

        if tools:
            # Langchain handles tool_choice seamlessly
            llm = llm.bind_tools(tools, tool_choice=tool_choice)

        logger.info(f"Making API call with model: {model}")
        print("DEBUG API PARAMS tools:", tools)
        try:
            response = await llm.ainvoke(messages)
            logger.debug(f"API call successful for model: {model}")
            return response
        except Exception as e:
            logger.error(f"API call failed for model {model}: {str(e)}")
            raise

    async def structured_response(
        self,
        user_input: Union[str, List[Dict[str, str]]],
        instructions: str,
        schema_model: Type[BaseModel],
        model: str = ResponseConfig.DEFAULT_MODEL,
        temperature: float = ResponseConfig.DEFAULT_TEMPERATURE,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        if not issubclass(schema_model, BaseModel):
            raise ValueError(
                f"schema_model must be a Pydantic BaseModel, got {type(schema_model)}"
            )

        messages = []
        if instructions:
            messages.append(SystemMessage(content=instructions))
        if isinstance(user_input, str):
            messages.append(HumanMessage(content=user_input))
        else:
            for msg in user_input:
                if msg.get("role") == "system":
                    messages.append(SystemMessage(content=msg.get("content", "")))
                else:
                    messages.append(HumanMessage(content=msg.get("content", "")))

        llm = ChatOpenAI(
            model=model,
            temperature=temperature if model not in ResponseConfig.MODELS_WITHOUT_TEMPERATURE else None,
            api_key=self.openai_api_key
        )

        logger.info(f"Making structured API call with model: {model}")
        try:
            # Langchain handles the prompt rewriting and tool calling transparently
            structured_llm = llm.with_structured_output(schema_model)
            response = await structured_llm.ainvoke(messages)
            logger.debug(f"API call successful for model: {model}")
            return response
        except Exception as e:
            logger.error(f"API call failed for model {model}: {str(e)}")
            raise