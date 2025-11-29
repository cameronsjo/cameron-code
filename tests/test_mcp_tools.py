"""Test custom MCP tools work through the SDK."""

import pytest
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    create_sdk_mcp_server,
    AssistantMessage,
    ResultMessage,
)

from cameron_code.tools import cameron_search, cameron_time


@pytest.mark.asyncio
async def test_custom_mcp_tool_search():
    """Verify custom MCP tool cameron_search works."""
    server = create_sdk_mcp_server(
        name="cameron-tools",
        tools=[cameron_search],
    )

    options = ClaudeAgentOptions(
        mcp_servers={"cameron": server},
        max_turns=3,
        permission_mode="bypassPermissions",  # Auto-allow tools for testing
    )

    messages = []
    async with ClaudeSDKClient(options) as client:
        # Use query() to send message after auto-connect
        await client.query(
            "Use the cameron_search tool to search for 'coffee'. Report what you find."
        )
        async for msg in client.receive_response():
            messages.append(msg)
            if isinstance(msg, AssistantMessage):
                print(f"Assistant: {msg}")

    # Should complete
    result = next((m for m in messages if isinstance(m, ResultMessage)), None)
    assert result is not None

    # The response should mention something about coffee/lattes
    assistant_content = ""
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if hasattr(block, "text"):
                    assistant_content += block.text

    # Should have used the tool and gotten a result
    assert "oat milk" in assistant_content.lower() or "latte" in assistant_content.lower()


@pytest.mark.asyncio
async def test_custom_mcp_tool_time():
    """Verify custom MCP tool cameron_time works."""
    server = create_sdk_mcp_server(
        name="cameron-tools",
        tools=[cameron_time],
    )

    options = ClaudeAgentOptions(
        mcp_servers={"cameron": server},
        max_turns=3,
        permission_mode="bypassPermissions",  # Auto-allow tools for testing
    )

    messages = []
    async with ClaudeSDKClient(options) as client:
        await client.query("Use the cameron_time tool to get the current time.")
        async for msg in client.receive_response():
            messages.append(msg)

    result = next((m for m in messages if isinstance(m, ResultMessage)), None)
    assert result is not None
