"""Test hooks (PreToolUse, PostToolUse) work through the SDK."""

import pytest
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    AssistantMessage,
    ResultMessage,
    PreToolUseHookInput,
    PostToolUseHookInput,
)


@pytest.mark.asyncio
async def test_pre_tool_hook_logging():
    """Verify PreToolUse hook is called before tool execution."""
    hook_calls: list[dict] = []

    async def pre_hook(
        input: PreToolUseHookInput,
        tool_use_id: str,
        context,
    ) -> dict:
        hook_calls.append(
            {
                "event": "pre",
                "tool_name": input.get("tool_name"),
                "tool_use_id": tool_use_id,
            }
        )
        return {"continue_": True}

    options = ClaudeAgentOptions(
        hooks={
            "PreToolUse": [HookMatcher(matcher="*", hooks=[pre_hook])],
        },
        max_turns=3,
    )

    async with ClaudeSDKClient(options) as client:
        await client.query("Run: echo 'testing hooks'")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                print(f"Assistant: {msg}")

    # Hook should have been called
    assert len(hook_calls) > 0
    assert hook_calls[0]["event"] == "pre"
    print(f"Pre-hook calls: {hook_calls}")


@pytest.mark.asyncio
async def test_post_tool_hook_logging():
    """Verify PostToolUse hook is called after tool execution."""
    hook_calls: list[dict] = []

    async def post_hook(
        input: PostToolUseHookInput,
        tool_use_id: str,
        context,
    ) -> dict:
        hook_calls.append(
            {
                "event": "post",
                "tool_name": input.get("tool_name"),
                "tool_output": input.get("tool_output"),
            }
        )
        return {"continue_": True}

    options = ClaudeAgentOptions(
        hooks={
            "PostToolUse": [HookMatcher(matcher="*", hooks=[post_hook])],
        },
        max_turns=3,
    )

    async with ClaudeSDKClient(options) as client:
        await client.query("Run: echo 'post hook test'")
        async for msg in client.receive_response():
            pass

    # Hook should have been called
    assert len(hook_calls) > 0
    assert hook_calls[0]["event"] == "post"
    print(f"Post-hook calls: {hook_calls}")


@pytest.mark.asyncio
async def test_pre_hook_can_block_tool():
    """Verify PreToolUse hook can block tool execution."""
    blocked = []

    async def blocking_hook(
        input: PreToolUseHookInput,
        tool_use_id: str,
        context,
    ) -> dict:
        tool_name = input.get("tool_name")
        tool_input = input.get("tool_input", {})

        # Block any command containing 'forbidden'
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if "forbidden" in command:
                blocked.append(command)
                return {
                    "continue_": False,
                    "output": "BLOCKED: This command is forbidden by Cameron Code",
                }

        return {"continue_": True}

    options = ClaudeAgentOptions(
        hooks={
            "PreToolUse": [HookMatcher(matcher="Bash", hooks=[blocking_hook])],
        },
        max_turns=3,
    )

    messages = []
    async with ClaudeSDKClient(options) as client:
        await client.query("Run this command: echo 'forbidden command'")
        async for msg in client.receive_response():
            messages.append(msg)

    # The command should have been blocked
    assert len(blocked) > 0
    print(f"Blocked commands: {blocked}")
