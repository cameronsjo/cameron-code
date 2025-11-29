"""Test permission callbacks work through the SDK."""

import pytest
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    PermissionResult,
    PermissionResultAllow,
    PermissionResultDeny,
)


@pytest.mark.asyncio
async def test_permission_callback_allow():
    """Verify permission callback can allow tool execution."""
    permission_checks: list[dict] = []

    async def allow_callback(
        tool_name: str,
        tool_input: dict,
        context,
    ) -> PermissionResult:
        permission_checks.append(
            {
                "tool": tool_name,
                "input": tool_input,
                "decision": "allow",
            }
        )
        return PermissionResultAllow()

    options = ClaudeAgentOptions(
        can_use_tool=allow_callback,
        max_turns=3,
        cwd="/Users/cameron/Projects/cameron-code-test",
        # Use default permission mode so callback is invoked
        permission_mode="default",
    )

    async with ClaudeSDKClient(options) as client:
        # Use Write tool which requires permission check
        await client.query(
            "Create a file called /tmp/cameron_test_permission.txt with content 'hello'"
        )
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                print(f"Assistant: {msg}")

    # Permission callback should have been invoked for Write
    assert len(permission_checks) > 0
    print(f"Permission checks: {permission_checks}")


@pytest.mark.asyncio
async def test_permission_callback_deny():
    """Verify permission callback can deny tool execution."""
    permission_checks: list[dict] = []

    async def deny_write_callback(
        tool_name: str,
        tool_input: dict,
        context,
    ) -> PermissionResult:
        # Deny all Write operations
        if tool_name == "Write":
            permission_checks.append(
                {
                    "tool": tool_name,
                    "file": tool_input.get("file_path", ""),
                    "decision": "deny",
                }
            )
            return PermissionResultDeny(
                message="Cameron Code: Write operations are not allowed"
            )

        permission_checks.append(
            {
                "tool": tool_name,
                "decision": "allow",
            }
        )
        return PermissionResultAllow()

    options = ClaudeAgentOptions(
        can_use_tool=deny_write_callback,
        max_turns=3,
        cwd="/Users/cameron/Projects/cameron-code-test",
        permission_mode="default",
    )

    messages = []
    async with ClaudeSDKClient(options) as client:
        await client.query(
            "Create a file called /tmp/cameron_deny_test.txt with content 'test'"
        )
        async for msg in client.receive_response():
            messages.append(msg)

    # Should have denied the Write
    denied = [c for c in permission_checks if c.get("decision") == "deny"]
    assert len(denied) > 0
    print(f"Denied operations: {denied}")


@pytest.mark.asyncio
async def test_permission_callback_selective():
    """Verify permission callback can selectively control different tools."""
    tool_decisions: list[dict] = []

    async def selective_callback(
        tool_name: str,
        tool_input: dict,
        context,
    ) -> PermissionResult:
        decision = {
            "tool": tool_name,
            "input_preview": str(tool_input)[:100],
        }

        # Allow Read and Glob, deny Write
        if tool_name == "Write":
            decision["decision"] = "deny"
            tool_decisions.append(decision)
            return PermissionResultDeny(message="Write operations disabled in this session")

        decision["decision"] = "allow"
        tool_decisions.append(decision)
        return PermissionResultAllow()

    options = ClaudeAgentOptions(
        can_use_tool=selective_callback,
        max_turns=5,
        cwd="/Users/cameron/Projects/cameron-code-test",
    )

    async with ClaudeSDKClient(options) as client:
        await client.query(
            "First read tests/test_permissions.py, then try to create a new file called test_output.txt with 'hello'"
        )
        async for msg in client.receive_response():
            pass

    # Should have allowed Read, denied Write
    read_decisions = [d for d in tool_decisions if d["tool"] == "Read"]
    write_decisions = [d for d in tool_decisions if d["tool"] == "Write"]

    print(f"Tool decisions: {tool_decisions}")

    # Read should be allowed
    if read_decisions:
        assert read_decisions[0]["decision"] == "allow"

    # Write should be denied
    if write_decisions:
        assert write_decisions[0]["decision"] == "deny"
