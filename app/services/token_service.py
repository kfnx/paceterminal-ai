"""Token service for fetching token data from database."""
from typing import Optional
from app.core.database import db


async def get_recent_tokens(limit: int = 50):
    """Fetch recent tokens for chat context."""
    try:
        tokens = await db.tokens.find_many(
            where={"archived_at": None},
            take=limit,
            order={"ordering": "asc"},
            include={"name": True, "address": True, "tier": True, "label": True},
        )
        return tokens
    except Exception as e:
        print(f"Error fetching tokens: {e}")
        return []


def build_token_context(tokens: list) -> str:
    """Build token context string for system prompt."""
    if not tokens:
        return ""

    token_list = ", ".join(
        [f"{t.name} (Tier {t.tier if t.tier else 'N/A'})" for t in tokens]
    )
    return f"\n\nCurrent tokens in PACETERMINAL database (for reference): {token_list}"


async def get_token_by_name(name: str) -> Optional[dict]:
    """
    Get detailed token information by name (case-insensitive search).

    Returns token with all details including teams, metrics, technical analysis.
    """
    try:
        token = await db.tokens.find_first(
            where={
                "archived_at": None,
                "name": {"contains": name, "mode": "insensitive"},
            },
            include={
                "teams": True,
                "metrics_static": True,
                "technical_analysis": True,
                "flywheels": True,
                "alpha": True,
            },
        )

        if not token:
            return None

        return {
            "address": token.address,
            "name": token.name,
            "tier": token.tier,
            "label": token.label,
            "description": token.description_en or token.description,
            "image": token.image,
            "teams": [
                {
                    "name": team.name,
                    "role": team.role,
                    "x_account": team.x_account,
                    "description": team.description,
                }
                for team in (token.teams or [])
            ],
            "metrics": [
                {
                    "label": metric.label_en or metric.label,
                    "value": metric.value_en or metric.value,
                    "description": metric.description_en or metric.description,
                    "source": metric.source,
                }
                for metric in (token.metrics_static or [])
            ],
            "technical_analysis": [
                {
                    "description": ta.description_en or ta.description,
                    "image": ta.image,
                }
                for ta in (token.technical_analysis or [])
            ],
            "alpha_info": [
                {
                    "title": alpha.title_en or alpha.title,
                    "text": alpha.text_en or alpha.text,
                }
                for alpha in (token.alpha or [])
            ],
            "has_flywheel": bool(token.flywheels),
        }
    except Exception as e:
        print(f"Error fetching token by name '{name}': {e}")
        return None


async def search_tokens(query: str, limit: int = 10) -> list[dict]:
    """
    Search tokens by name or label (case-insensitive).

    Returns basic token information for matching tokens.
    """
    try:
        tokens = await db.tokens.find_many(
            where={
                "archived_at": None,
                "OR": [
                    {"name": {"contains": query, "mode": "insensitive"}},
                    {"label": {"contains": query, "mode": "insensitive"}},
                ],
            },
            take=limit,
            order={"ordering": "asc"},
        )

        return [
            {
                "address": token.address,
                "name": token.name,
                "tier": token.tier,
                "label": token.label,
                "description": (token.description_en or token.description or "")[:200],
            }
            for token in tokens
        ]
    except Exception as e:
        print(f"Error searching tokens with query '{query}': {e}")
        return []