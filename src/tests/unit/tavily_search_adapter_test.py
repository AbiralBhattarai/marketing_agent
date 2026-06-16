import asyncio
import os
from dotenv import load_dotenv
from src.adapters.tavily_search_adapter import TavilySearchAdapter
from src.adapters.open_ai_adapter import AsyncOpenAIApiAdapter
from src.domain.models.input import SearchResultsFromQuery

load_dotenv()


async def main():
    adapter = TavilySearchAdapter(
        api_key=os.getenv("TAVILY_API_KEY"),
    )
    query = "I want to promote my nike air force 1s and i have a budget of 20000$"
    llm = AsyncOpenAIApiAdapter()
    extracted_item = await llm.structured_response(user_input=query,instructions="Extract the physical_item,online_service or instore_experience from the user query and the cateogry of the item. The category need to be one word.",schema_model=SearchResultsFromQuery)
    print(extracted_item.model_dump())
    print(type(extracted_item))
    res = await adapter.search_web(extracted_item.item)


    print(res)


if __name__ == "__main__":
    asyncio.run(main())