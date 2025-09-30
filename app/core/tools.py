"""OpenAI function/tool definitions for PACETERMINAL."""

import json
from app.services.token_service import get_token_by_name, search_tokens


# Tool definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_token_info",
            "description": "Get detailed information about a specific token listed on PACETERMINAL. Use this when users ask about a specific token's details, team, metrics, or analysis. Returns comprehensive token data including tier, description, team members, metrics, and technical analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_name": {
                        "type": "string",
                        "description": "The name of the token to look up (case-insensitive, partial matches supported)",
                    }
                },
                "required": ["token_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_tokens",
            "description": "Search for tokens on PACETERMINAL by name or label. Use this when users want to find tokens, list tokens, or search for tokens matching certain criteria. Returns a list of matching tokens with basic information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to match against token names or labels",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
]


async def execute_function(function_name: str, arguments: dict) -> str:
    """
    Execute a tool function and return the result as JSON string.

    Args:
        function_name: Name of the function to execute
        arguments: Function arguments as dictionary

    Returns:
        JSON string containing the function result
    """
    try:
        if function_name == "get_token_info":
            token_name = arguments.get("token_name")
            result = await get_token_by_name(token_name)

            if result is None:
                return json.dumps(
                    {
                        "error": f"Token '{token_name}' not found in PACETERMINAL database. It may not be listed yet or the name might be incorrect."
                    }
                )

            return json.dumps(result)

        elif function_name == "search_tokens":
            query = arguments.get("query")
            limit = arguments.get("limit", 10)
            results = await search_tokens(query, limit)

            if not results:
                return json.dumps(
                    {
                        "message": f"No tokens found matching '{query}'. The database may not have tokens matching this criteria."
                    }
                )

            return json.dumps({"results": results, "count": len(results)})

        else:
            return json.dumps({"error": f"Unknown function: {function_name}"})

    except Exception as e:
        print(f"Error executing function {function_name}: {e}")
        return json.dumps({"error": f"Error executing function: {str(e)}"})
