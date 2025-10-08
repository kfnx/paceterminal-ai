from pydantic import BaseModel


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int | None = None
