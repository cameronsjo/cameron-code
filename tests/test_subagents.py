"""Test that subagents (Task tool) work through the SDK."""

import pytest
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
)


@pytest.mark.asyncio
async def test_task_tool_subagent():
    """Verify Task tool can spawn subagents."""
    messages = []

    options = ClaudeAgentOptions(
        max_turns=10,  # Subagents need more turns
        cwd="/Users/cameron/Projects/cameron-code-test",
        allowed_tools=["Task", "Read", "Glob", "Grep"],  # Enable Task tool
    )

    async with ClaudeSDKClient(options) as client:
        await client.query(
            "Use the Task tool with subagent_type='Explore' to find what Python files exist in src/. "
            "Just report the file names."
        )
        async for msg in client.receive_response():
            messages.append(msg)
            if isinstance(msg, AssistantMessage):
                print(f"Assistant message received")

    # Should complete
    result = next((m for m in messages if isinstance(m, ResultMessage)), None)
    assert result is not None
    print(f"Result: {result}")


@pytest.mark.asyncio
async def test_subagent_explore_codebase():
    """Verify Explore subagent can analyze codebase structure."""
    messages = []

    options = ClaudeAgentOptions(
        max_turns=15,
        cwd="/Users/cameron/Projects/cameron-code-test",
    )

    async with ClaudeSDKClient(options) as client:
        await client.query(
            "Use the Task tool with subagent_type='Explore' and a prompt asking it to "
            "describe the structure of this project. Keep it brief."
        )
        async for msg in client.receive_response():
            messages.append(msg)

    result = next((m for m in messages if isinstance(m, ResultMessage)), None)
    assert result is not None

    # Check we got substantive response
    assistant_msgs = [m for m in messages if isinstance(m, AssistantMessage)]
    assert len(assistant_msgs) > 0
