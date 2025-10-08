from openai import AsyncOpenAI
from tavily import AsyncTavilyClient

from app.core.config import settings

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
tavily_client = AsyncTavilyClient(
    api_key=settings.TAVILY_API_KEY,
)
