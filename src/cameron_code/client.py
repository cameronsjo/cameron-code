"""Cameron Code client - wraps Claude Agent SDK with custom capabilities."""

from typing import AsyncIterator, Callable, Any
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    create_sdk_mcp_server,
    Message,
    PermissionResult,
    PermissionResultAllow,
    PermissionResultDeny,
    HookMatcher,
    PreToolUseHookInput,
    PostToolUseHookInput,
)

from .tools import cameron_search, cameron_time


class CameronCodeClient:
    """Extended Claude Code client with custom tools, hooks, and permissions."""

    def __init__(
        self,
        *,
        cwd: str | None = None,
        permission_callback: Callable[..., PermissionResult] | None = None,
        pre_tool_hook: Callable[..., dict] | None = None,
        post_tool_hook: Callable[..., dict] | None = None,
        audit_log: list[dict] | None = None,
        allowed_tools: list[str] | None = None,
        setting_sources: list[str] | None = None,
    ) -> None:
        self.cwd = cwd
        self.custom_permission_callback = permission_callback
        self.custom_pre_tool_hook = pre_tool_hook
        self.custom_post_tool_hook = post_tool_hook
        self.audit_log = audit_log if audit_log is not None else []
        self.allowed_tools = allowed_tools
        # Default to loading project settings for slash commands
        self.setting_sources = setting_sources if setting_sources is not None else ["project"]
        self._client: ClaudeSDKClient | None = None

    async def _default_permission_callback(
        self,
        tool_name: str,
        tool_input: dict,
        context: Any,
    ) -> PermissionResult:
        """Default permission callback - logs and allows most tools."""
        self.audit_log.append(
            {
                "event": "permission_check",
                "tool": tool_name,
                "input": tool_input,
            }
        )

        # Block dangerous bash commands
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            dangerous_patterns = ["rm -rf /", ":(){ :|:& };:", "mkfs", "> /dev/sda"]
            for pattern in dangerous_patterns:
                if pattern in command:
                    return PermissionResultDeny(
                        message=f"Cameron Code blocked dangerous command: {pattern}"
                    )

        # Delegate to custom callback if provided
        if self.custom_permission_callback:
            return await self.custom_permission_callback(tool_name, tool_input, context)

        return PermissionResultAllow()

    async def _pre_tool_hook(
        self,
        input: PreToolUseHookInput,
        tool_use_id: str,
        context: Any,
    ) -> dict:
        """Pre-tool execution hook - logs before tool runs."""
        self.audit_log.append(
            {
                "event": "pre_tool",
                "tool_use_id": tool_use_id,
                "tool_name": input.get("tool_name"),
                "tool_input": input.get("tool_input"),
            }
        )

        if self.custom_pre_tool_hook:
            return await self.custom_pre_tool_hook(input, tool_use_id, context)

        return {"continue_": True}

    async def _post_tool_hook(
        self,
        input: PostToolUseHookInput,
        tool_use_id: str,
        context: Any,
    ) -> dict:
        """Post-tool execution hook - logs after tool runs."""
        self.audit_log.append(
            {
                "event": "post_tool",
                "tool_use_id": tool_use_id,
                "tool_name": input.get("tool_name"),
                "tool_output": input.get("tool_output"),
            }
        )

        if self.custom_post_tool_hook:
            return await self.custom_post_tool_hook(input, tool_use_id, context)

        return {"continue_": True}

    def _build_options(self) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions with all Cameron Code features."""
        # Create MCP server with custom tools
        cameron_server = create_sdk_mcp_server(
            name="cameron-tools",
            tools=[cameron_search, cameron_time],
        )

        # Build hooks configuration
        hooks = {
            "PreToolUse": [
                HookMatcher(matcher="*", hooks=[self._pre_tool_hook]),
            ],
            "PostToolUse": [
                HookMatcher(matcher="*", hooks=[self._post_tool_hook]),
            ],
        }

        return ClaudeAgentOptions(
            cwd=self.cwd,
            can_use_tool=self._default_permission_callback,
            mcp_servers={"cameron": cameron_server},
            hooks=hooks,
            allowed_tools=self.allowed_tools,
            setting_sources=self.setting_sources,  # Enable slash commands
        )

    async def __aenter__(self) -> "CameronCodeClient":
        """Async context manager entry."""
        options = self._build_options()
        self._client = ClaudeSDKClient(options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    async def connect(self, prompt: str | None = None) -> None:
        """Connect to Claude Code with optional initial prompt."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        await self._client.connect(prompt)

    async def query(self, prompt: str) -> None:
        """Send a query to the connected session."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        await self._client.query(prompt)

    async def receive_response(self) -> AsyncIterator[Message]:
        """Receive messages until a result is returned."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        async for message in self._client.receive_response():
            yield message

    async def receive_messages(self) -> AsyncIterator[Message]:
        """Receive all messages (doesn't stop at result)."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        async for message in self._client.receive_messages():
            yield message

    def get_audit_log(self) -> list[dict]:
        """Get the audit log of all tool executions."""
        return self.audit_log.copy()

    async def get_server_info(self) -> dict | None:
        """Get server info including available slash commands."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        return await self._client.get_server_info()

    async def get_available_commands(self) -> list[dict]:
        """Get list of available slash commands."""
        info = await self.get_server_info()
        if info:
            return info.get("commands", [])
        return []
