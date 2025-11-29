"""Test that native Claude Code tools work through the SDK."""

import pytest
from claude_agent_sdk import query, AssistantMessage, ResultMessage, ClaudeAgentOptions


@pytest.mark.asyncio
async def test_bash_tool():
    """Verify Bash tool works - simple echo command."""
    messages = []

    options = ClaudeAgentOptions(max_turns=3)

    async for msg in query(
        prompt="Run this exact command: echo 'hello from cameron code'",
        options=options,
    ):
        messages.append(msg)
        if isinstance(msg, AssistantMessage):
            print(f"Assistant: {msg}")

    # Should have received messages
    assert len(messages) > 0

    # Should have a result
    result = next((m for m in messages if isinstance(m, ResultMessage)), None)
    assert result is not None


@pytest.mark.asyncio
async def test_read_tool():
    """Verify Read tool works - read this test file."""
    messages = []

    options = ClaudeAgentOptions(
        max_turns=3,
        cwd="/Users/cameron/Projects/cameron-code-test",
    )

    async for msg in query(
        prompt="Read the file tests/test_native_tools.py and tell me what the first test function is named",
        options=options,
    ):
        messages.append(msg)

    # Should complete successfully
    result = next((m for m in messages if isinstance(m, ResultMessage)), None)
    assert result is not None

    # Check if test_bash_tool was mentioned in the response
    assistant_msgs = [m for m in messages if isinstance(m, AssistantMessage)]
    assert len(assistant_msgs) > 0


@pytest.mark.asyncio
async def test_glob_tool():
    """Verify Glob tool works - find Python files."""
    messages = []

    options = ClaudeAgentOptions(
        max_turns=3,
        cwd="/Users/cameron/Projects/cameron-code-test",
    )

    async for msg in query(
        prompt="Use the Glob tool to find all .py files in the src/ directory. Just list them.",
        options=options,
    ):
        messages.append(msg)

    result = next((m for m in messages if isinstance(m, ResultMessage)), None)
    assert result is not None
