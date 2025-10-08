import json
from app.llm.utils import openai_client
from app.schemas.chat import ChatRequest
from app.core.prompts import build_system_prompt_with_context
from app.services.token_service import get_recent_tokens, build_token_context
from app.core.tools import TOOLS, execute_function


async def stream_chat_completion(request: ChatRequest):
    """
    Stream chat completion from OpenAI with PACETERMINAL context and function calling.

    Supports OpenAI function calling to retrieve token information from the database.
    """
    # Fetch recent tokens for context
    tokens = await get_recent_tokens(limit=50)
    token_context = build_token_context(tokens)

    # Build system prompt with token context
    system_prompt = build_system_prompt_with_context(token_context)

    # Prepare messages with system prompt
    messages = [{"role": "system", "content": system_prompt}] + request.messages

    # Initial API call with tools
    response = await openai_client.chat.completions.create(
        model=request.model,
        messages=messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens or 1000,
        tools=TOOLS,
        tool_choice="auto",
        stream=False,  # First call non-streaming to check for tool calls
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # If no tool calls, stream the response
    if not tool_calls:
        # Re-run with streaming for the final response
        stream = await openai_client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens or 1000,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
        return

    # Process tool calls
    messages.append(response_message)

    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)

        # Execute the function
        function_response = await execute_function(function_name, function_args)

        # Add function response to messages
        messages.append(
            {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            }
        )

    # Get final response with function results and stream it
    stream = await openai_client.chat.completions.create(
        model=request.model,
        messages=messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens or 1000,
        stream=True,
    )

    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
