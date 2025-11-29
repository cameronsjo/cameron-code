"""Test slash commands workaround using setting_sources.

The key insight: By default, setting_sources=None means NO settings are loaded,
including slash commands. To enable slash commands, set setting_sources=["project"].
"""

import pytest
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    SystemMessage,
)


def extract_slash_commands(msg: SystemMessage) -> list[str]:
    """Extract slash command names from system init message."""
    if msg.subtype == "init":
        return msg.data.get("slash_commands", [])
    return []


@pytest.mark.asyncio
async def test_slash_commands_not_loaded_by_default():
    """Verify slash commands are NOT loaded when setting_sources is None (default)."""
    options = ClaudeAgentOptions(
        max_turns=1,
        cwd="/Users/cameron/Projects/cameron-code-test",
        # setting_sources=None is default - NO settings loaded
    )

    slash_commands = []
    async with ClaudeSDKClient(options) as client:
        await client.query("What is 2+2?")
        async for msg in client.receive_response():
            if isinstance(msg, SystemMessage) and msg.subtype == "init":
                slash_commands = extract_slash_commands(msg)
                print(f"Commands (default): {slash_commands}")
                break

    # Our custom commands should NOT be available
    assert "greet" not in slash_commands
    assert "analyze" not in slash_commands


@pytest.mark.asyncio
async def test_slash_commands_loaded_with_project_source():
    """Verify slash commands ARE loaded when setting_sources includes 'project'."""
    options = ClaudeAgentOptions(
        max_turns=1,
        cwd="/Users/cameron/Projects/cameron-code-test",
        setting_sources=["project"],  # Load project settings including .claude/commands/
    )

    slash_commands = []
    async with ClaudeSDKClient(options) as client:
        await client.query("What is 2+2?")
        async for msg in client.receive_response():
            if isinstance(msg, SystemMessage) and msg.subtype == "init":
                slash_commands = extract_slash_commands(msg)
                print(f"Commands (project): {slash_commands}")
                break

    # Our custom commands SHOULD be available
    assert "greet" in slash_commands or any("greet" in cmd for cmd in slash_commands)
    assert "analyze" in slash_commands or any("analyze" in cmd for cmd in slash_commands)


@pytest.mark.asyncio
async def test_slash_command_execution_with_setting_sources():
    """Verify slash commands actually work when setting_sources is set."""
    options = ClaudeAgentOptions(
        max_turns=3,
        cwd="/Users/cameron/Projects/cameron-code-test",
        setting_sources=["project"],  # Enable project settings
    )

    messages = []
    async with ClaudeSDKClient(options) as client:
        # Now /greet should expand!
        await client.query("/greet")
        async for msg in client.receive_response():
            messages.append(msg)
            if isinstance(msg, AssistantMessage):
                print(f"Assistant: {msg}")

    result = next((m for m in messages if isinstance(m, ResultMessage)), None)
    assert result is not None

    # Should mention "Cameron Code" from the slash command expansion
    assistant_content = ""
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if hasattr(block, "text"):
                    assistant_content += block.text.lower()

    # The greeting should reference Cameron Code or custom capabilities
    assert "cameron" in assistant_content or "custom" in assistant_content or "hello" in assistant_content


@pytest.mark.asyncio
async def test_get_server_info_shows_commands():
    """Verify get_server_info() returns available slash commands."""
    options = ClaudeAgentOptions(
        max_turns=1,
        cwd="/Users/cameron/Projects/cameron-code-test",
        setting_sources=["project"],
    )

    async with ClaudeSDKClient(options) as client:
        await client.query("hi")

        # Consume one message to trigger init
        async for msg in client.receive_response():
            break

        # Check server info
        info = await client.get_server_info()
        print(f"Server info: {info}")

        if info:
            # Commands are in 'commands' key, not 'slash_commands'
            commands = info.get("commands", [])
            print(f"Available commands: {[c.get('name') for c in commands]}")
            # Should have our custom commands
            assert len(commands) > 0
            command_names = [c.get("name") for c in commands]
            assert "greet" in command_names
            assert "analyze" in command_names
