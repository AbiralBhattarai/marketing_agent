from src.adapters.open_ai_adapter import AsyncOpenAIApiAdapter
async def get_llm():
    return AsyncOpenAIApiAdapter()