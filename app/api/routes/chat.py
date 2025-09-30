from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from app.schemas.chat import ChatRequest
from app.services.openai_service import stream_chat_completion
from app.api.dependencies import limiter
from app.core.config import settings

router = APIRouter()


@router.post("/chat")
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def chat(request: Request, chat_request: ChatRequest):
    """
    PACETERMINAL AI Chat endpoint with streaming support.

    Features:
    - Streaming OpenAI responses
    - Rate limiting (configurable via RATE_LIMIT_CHAT env var)
    - PACETERMINAL-specific system prompt
    - Dynamic token database context
    - Input validation

    Returns:
    - Streaming text/event-stream response
    """
    try:
        # Validate messages array
        if not chat_request.messages or len(chat_request.messages) == 0:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid request",
                    "message": "Messages array cannot be empty.",
                },
            )

        # Validate message format
        for msg in chat_request.messages:
            if "role" not in msg or "content" not in msg:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Invalid request",
                        "message": "Each message must have 'role' and 'content' fields.",
                    },
                )

        return StreamingResponse(
            stream_chat_completion(chat_request), media_type="text/event-stream"
        )

    except Exception as e:
        print(f"Chatbot API error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "Sorry, I encountered an error. Please try again.",
            },
        )