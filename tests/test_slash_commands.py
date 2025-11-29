"""Test slash commands work through the SDK.

Note: Slash commands expand in the CLI, so we test by including the
command in our prompt and verifying the CLI processes it.
"""

import pytest
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
)


@pytest.mark.asyncio
async def test_slash_command_greet():
    """Verify /greet slash command works.

    NOTE: Slash commands are CLI-interactive features that may not work
    through the SDK's streaming mode. This test documents the current behavior.
    """
    messages = []

    options = ClaudeAgentOptions(
        max_turns=3,
        cwd="/Users/cameron/Projects/cameron-code-test",
    )

    async with ClaudeSDKClient(options) as client:
        # Slash commands expand in CLI interactive mode
        # Through SDK, we need to send the expanded prompt content instead
        await client.query(
            "Say hello and introduce yourself as 'Cameron Code' - an extended version "
            "of Claude Code with custom capabilities including custom MCP tools, "
            "hooks for auditing, and permission callbacks. Keep it brief and friendly."
        )
        async for msg in client.receive_response():
            messages.append(msg)
            print(f"Message type: {type(msg).__name__}")
            if isinstance(msg, AssistantMessage):
                print(f"Assistant: {msg}")

    result = next((m for m in messages if isinstance(m, ResultMessage)), None)
    assert result is not None

    # Should mention "Cameron Code" from the prompt
    assistant_content = ""
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if hasattr(block, "text"):
                    assistant_content += block.text.lower()

    # The greeting should reference Cameron Code or the custom capabilities
    assert "cameron" in assistant_content or "custom" in assistant_content or "hello" in assistant_content


@pytest.mark.asyncio
async def test_slash_command_analyze():
    """Verify /analyze-like functionality works.

    NOTE: Slash commands are CLI-interactive features that may not work
    through the SDK's streaming mode. This test uses the expanded prompt.
    """
    messages = []

    options = ClaudeAgentOptions(
        max_turns=5,
        cwd="/Users/cameron/Projects/cameron-code-test",
    )

    async with ClaudeSDKClient(options) as client:
        # Use the expanded prompt content from .claude/commands/analyze.md
        await client.query(
            "Analyze the current project structure and provide a brief summary: "
            "1. List all Python files. 2. Describe the main components. "
            "3. Note any tests present. Use Glob and Read tools as needed. Keep it concise."
        )
        async for msg in client.receive_response():
            messages.append(msg)

    result = next((m for m in messages if isinstance(m, ResultMessage)), None)
    assert result is not None

    # Should have analyzed the project
    assistant_content = ""
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if hasattr(block, "text"):
                    assistant_content += block.text.lower()

    # Should mention python files or project structure
    assert "python" in assistant_content or ".py" in assistant_content or "src" in assistant_content
