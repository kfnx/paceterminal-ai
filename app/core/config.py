import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # App
    APP_NAME: str = "PaceTerminal AI"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # CORS
    ALLOWED_ORIGINS: list[str] = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,https://paceterminal.com"
    ).split(",")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Tavily
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DIRECT_URL: str = os.getenv("DIRECT_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Rate Limiting
    RATE_LIMIT_CHAT: str = os.getenv(
        "RATE_LIMIT_CHAT", "10/minute"
    )  # 10 requests per minute per IP
    RATE_LIMIT_ANALYSIS: str = os.getenv(
        "RATE_LIMIT_ANALYSIS", "3/minute"
    )  # 3 analysis requests per minute per IP


settings = Settings()
