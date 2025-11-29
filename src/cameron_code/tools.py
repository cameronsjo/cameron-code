"""Custom MCP tools for Cameron Code."""

from claude_agent_sdk import tool
from datetime import datetime, timezone


@tool(
    name="cameron_search",
    description="Search Cameron's private knowledge base for information",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
        },
        "required": ["query"],
    },
)
async def cameron_search(args: dict) -> dict:
    """Simulate searching a private knowledge base."""
    query = args.get("query", "")

    # Simulated knowledge base
    knowledge = {
        "favorite_color": "Cameron's favorite color is blue.",
        "project": "Cameron is working on extending Claude Code.",
        "coffee": "Cameron prefers oat milk lattes.",
    }

    # Simple keyword matching
    results = []
    for key, value in knowledge.items():
        if query.lower() in key.lower() or query.lower() in value.lower():
            results.append(value)

    if not results:
        results = [f"No results found for '{query}' in Cameron's knowledge base."]

    return {
        "content": [{"type": "text", "text": "\n".join(results)}],
    }


@tool(
    name="cameron_time",
    description="Get the current time in Cameron's timezone (CST)",
    input_schema={
        "type": "object",
        "properties": {},
    },
)
async def cameron_time(args: dict) -> dict:
    """Return current time."""
    now = datetime.now(timezone.utc)
    return {
        "content": [
            {
                "type": "text",
                "text": f"Current UTC time: {now.isoformat()}",
            }
        ],
    }
