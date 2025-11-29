"""Cameron Code TUI - A simple terminal interface for Claude Code SDK."""

import asyncio
import random
from datetime import datetime
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Static,
    LoadingIndicator,
    ProgressBar,
)

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ThinkingBlock,
    HookMatcher,
    PreToolUseHookInput,
    PostToolUseHookInput,
)

from .tools import cameron_search, cameron_time
from claude_agent_sdk import create_sdk_mcp_server


# Custom thinking verbs inspired by tweakcc
THINKING_VERBS = [
    "Pondering",
    "Contemplating",
    "Mulling over",
    "Considering",
    "Reasoning",
    "Analyzing",
    "Processing",
    "Cogitating",
    "Deliberating",
    "Ruminating",
    "Musing",
    "Reflecting",
    "Weighing options",
    "Brainstorming",
    "Synthesizing",
]

# Tool-specific verbs
TOOL_VERBS = {
    "Bash": ["Executing", "Running", "Processing"],
    "Read": ["Reading", "Scanning", "Loading"],
    "Write": ["Writing", "Saving", "Creating"],
    "Edit": ["Editing", "Modifying", "Updating"],
    "Glob": ["Searching", "Finding", "Locating"],
    "Grep": ["Searching", "Matching", "Scanning"],
    "Task": ["Spawning", "Delegating", "Launching"],
    "WebFetch": ["Fetching", "Downloading", "Retrieving"],
    "WebSearch": ["Searching", "Querying", "Looking up"],
}


class MessageDisplay(Static):
    """A single message in the chat."""

    def __init__(self, role: str, content: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.role = role
        self.content = content

    def compose(self) -> ComposeResult:
        role_display = {
            "user": "You",
            "assistant": "Cameron",
            "system": "System",
            "tool": "Tool",
            "thinking": "Thinking",
            "hook": "Hook",
        }.get(self.role, self.role)

        role_class = f"role-{self.role}"
        yield Label(f"[bold]{role_display}[/bold]", classes=f"message-role {role_class}")
        yield Markdown(self.content, classes="message-content")


class ThinkingIndicator(Static):
    """Animated thinking indicator with custom verbs."""

    def __init__(self, tool_name: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.verb_index = 0

        # Use tool-specific verbs if available
        if tool_name and tool_name in TOOL_VERBS:
            self.verbs = TOOL_VERBS[tool_name]
        else:
            self.verbs = THINKING_VERBS

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()
        initial_verb = self.verbs[0]
        if self.tool_name:
            initial_verb = f"{initial_verb} ({self.tool_name})"
        yield Label(initial_verb, id="thinking-verb")

    def on_mount(self) -> None:
        self.set_interval(0.6, self._rotate_verb)

    def _rotate_verb(self) -> None:
        self.verb_index = (self.verb_index + 1) % len(self.verbs)
        verb = self.verbs[self.verb_index]
        if self.tool_name:
            verb = f"{verb} ({self.tool_name})"
        try:
            verb_label = self.query_one("#thinking-verb", Label)
            verb_label.update(verb)
        except Exception:
            pass


class ChatContainer(VerticalScroll):
    """Container for chat messages."""

    def add_message(self, role: str, content: str) -> None:
        msg = MessageDisplay(role, content)
        self.mount(msg)
        self.scroll_end(animate=False)


class CameronCodeApp(App):
    """Cameron Code TUI Application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #chat-container {
        height: 1fr;
        padding: 1;
        border: solid $primary;
    }

    MessageDisplay {
        margin-bottom: 1;
        padding: 1;
        background: $surface-darken-1;
    }

    .message-role {
        margin-bottom: 1;
    }

    .role-user {
        color: $success;
    }

    .role-assistant {
        color: $primary;
    }

    .role-system {
        color: $warning;
    }

    .role-tool {
        color: $secondary;
    }

    .role-thinking {
        color: $text-muted;
        text-style: italic;
    }

    .role-hook {
        color: #888888;
        text-style: dim;
    }

    .message-content {
        padding-left: 2;
    }

    #input-container {
        height: auto;
        dock: bottom;
        padding: 1;
    }

    #prompt-input {
        width: 100%;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $primary-darken-2;
        padding: 0 1;
    }

    ThinkingIndicator {
        height: 3;
        align: center middle;
    }

    ThinkingIndicator LoadingIndicator {
        width: auto;
    }

    #thinking-verb {
        margin-left: 1;
        color: $text-muted;
        text-style: italic;
    }

    #cost-display {
        dock: right;
        width: auto;
    }

    #model-display {
        dock: right;
        width: auto;
        margin-right: 2;
        color: $text-muted;
    }

    #turns-display {
        dock: right;
        width: auto;
        margin-right: 2;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+m", "switch_model", "Model"),
        Binding("ctrl+h", "toggle_hooks", "Hooks"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.client: ClaudeSDKClient | None = None
        self.total_cost: float = 0.0
        self.total_turns: int = 0
        self.is_processing = False
        self._thinking_indicator: ThinkingIndicator | None = None
        self.current_model = "sonnet"
        self.show_hooks = False
        self.tool_timings: dict[str, float] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ChatContainer(id="chat-container")
        with Container(id="input-container"):
            yield Input(placeholder="Ask Cameron anything... (or /command)", id="prompt-input")
        with Horizontal(id="status-bar"):
            yield Label("Ready", id="status-label")
            yield Label("", id="turns-display")
            yield Label("sonnet", id="model-display")
            yield Label("$0.0000", id="cost-display")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the Claude client on mount."""
        self.query_one("#prompt-input", Input).focus()

        chat = self.query_one("#chat-container", ChatContainer)
        chat.add_message(
            "system",
            "Welcome to **Cameron Code**!\n\n"
            "Features:\n"
            "- Custom MCP tools (`cameron_search`, `cameron_time`)\n"
            "- Pre/Post tool hooks with timing\n"
            "- Slash command support\n"
            "- Model switching (Ctrl+M)\n\n"
            "Bindings: `Ctrl+L` clear, `Ctrl+M` model, `Ctrl+H` hooks, `Esc` cancel"
        )

        await self._init_client()

    async def _pre_tool_hook(
        self,
        input: PreToolUseHookInput,
        tool_use_id: str,
        context: Any,
    ) -> dict:
        """Pre-tool hook - show what's about to run."""
        tool_name = input.get("tool_name", "Unknown")
        self.tool_timings[tool_use_id] = asyncio.get_event_loop().time()

        if self.show_hooks:
            chat = self.query_one("#chat-container", ChatContainer)
            tool_input = input.get("tool_input", {})
            preview = str(tool_input)[:100]
            if len(str(tool_input)) > 100:
                preview += "..."
            chat.add_message("hook", f"**PreToolUse**: {tool_name}\n```\n{preview}\n```")

        # Update thinking indicator with tool name
        self._show_thinking(tool_name)

        return {"continue_": True}

    async def _post_tool_hook(
        self,
        input: PostToolUseHookInput,
        tool_use_id: str,
        context: Any,
    ) -> dict:
        """Post-tool hook - show timing."""
        tool_name = input.get("tool_name", "Unknown")

        # Calculate timing
        start_time = self.tool_timings.pop(tool_use_id, None)
        if start_time:
            duration = asyncio.get_event_loop().time() - start_time
            duration_str = f"{duration:.2f}s"
        else:
            duration_str = "?"

        if self.show_hooks:
            chat = self.query_one("#chat-container", ChatContainer)
            output = input.get("tool_output", "")
            if isinstance(output, str):
                preview = output[:100]
                if len(output) > 100:
                    preview += "..."
            else:
                preview = str(output)[:100]
            chat.add_message("hook", f"**PostToolUse**: {tool_name} ({duration_str})\n```\n{preview}\n```")

        self._hide_thinking()

        return {"continue_": True}

    async def _init_client(self) -> None:
        """Initialize the Claude SDK client."""
        cameron_server = create_sdk_mcp_server(
            name="cameron-tools",
            tools=[cameron_search, cameron_time],
        )

        # Build hooks
        hooks = {
            "PreToolUse": [
                HookMatcher(matcher="*", hooks=[self._pre_tool_hook]),
            ],
            "PostToolUse": [
                HookMatcher(matcher="*", hooks=[self._post_tool_hook]),
            ],
        }

        options = ClaudeAgentOptions(
            mcp_servers={"cameron": cameron_server},
            setting_sources=["user", "project"],
            hooks=hooks,
            cwd=".",
            max_turns=25,
        )

        self.client = ClaudeSDKClient(options)
        await self.client.connect()

        # Show available commands
        info = await self.client.get_server_info()
        if info:
            commands = info.get("commands", [])
            if commands:
                cmd_list = ", ".join(f"`/{c['name']}`" for c in commands[:8])
                chat = self.query_one("#chat-container", ChatContainer)
                chat.add_message("system", f"Commands: {cmd_list}...")

    def _update_status(self, text: str) -> None:
        self.query_one("#status-label", Label).update(text)

    def _update_cost(self) -> None:
        self.query_one("#cost-display", Label).update(f"${self.total_cost:.4f}")

    def _update_turns(self) -> None:
        self.query_one("#turns-display", Label).update(f"turns: {self.total_turns}")

    def _show_thinking(self, tool_name: str | None = None) -> None:
        self._hide_thinking()  # Remove existing first
        self._thinking_indicator = ThinkingIndicator(tool_name=tool_name)
        chat = self.query_one("#chat-container", ChatContainer)
        chat.mount(self._thinking_indicator)
        chat.scroll_end(animate=False)

    def _hide_thinking(self) -> None:
        if self._thinking_indicator:
            self._thinking_indicator.remove()
            self._thinking_indicator = None

    @on(Input.Submitted, "#prompt-input")
    async def handle_input(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        if self.is_processing:
            return

        prompt = event.value.strip()
        if not prompt:
            return

        event.input.value = ""

        chat = self.query_one("#chat-container", ChatContainer)
        chat.add_message("user", prompt)

        await self._process_query(prompt)

    async def _process_query(self, prompt: str) -> None:
        """Process a query through Claude."""
        if not self.client:
            return

        self.is_processing = True
        self._update_status("Processing...")
        self._show_thinking()

        chat = self.query_one("#chat-container", ChatContainer)

        try:
            await self.client.query(prompt)

            current_text = ""
            tool_results_pending = False

            async for msg in self.client.receive_response():
                if isinstance(msg, AssistantMessage):
                    # First, output any accumulated text before tool use
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            current_text += block.text
                        elif isinstance(block, ToolUseBlock):
                            # Output text before tool
                            if current_text.strip():
                                self._hide_thinking()
                                chat.add_message("assistant", current_text)
                                current_text = ""
                            chat.add_message("tool", f"**{block.name}**")
                            tool_results_pending = True
                        elif isinstance(block, ToolResultBlock):
                            tool_results_pending = False
                        elif isinstance(block, ThinkingBlock):
                            if block.thinking:
                                preview = block.thinking[:150]
                                if len(block.thinking) > 150:
                                    preview += "..."
                                chat.add_message("thinking", f"_{preview}_")

                elif isinstance(msg, ResultMessage):
                    self._hide_thinking()
                    if current_text.strip():
                        chat.add_message("assistant", current_text)
                        current_text = ""

                    if msg.total_cost_usd:
                        self.total_cost += msg.total_cost_usd
                        self._update_cost()

                    if msg.num_turns:
                        self.total_turns += msg.num_turns
                        self._update_turns()

                    self._update_status("Ready")

        except Exception as e:
            self._hide_thinking()
            chat.add_message("system", f"**Error:** {e}")
            self._update_status("Error")

        finally:
            self.is_processing = False
            self._hide_thinking()
            self._update_status("Ready")

    def action_clear(self) -> None:
        """Clear the chat history."""
        chat = self.query_one("#chat-container", ChatContainer)
        chat.remove_children()
        chat.add_message("system", "Chat cleared.")

    async def action_cancel(self) -> None:
        """Cancel current operation."""
        if self.client and self.is_processing:
            await self.client.interrupt()
            self._hide_thinking()
            self._update_status("Cancelled")
            self.is_processing = False

    async def action_switch_model(self) -> None:
        """Switch between models."""
        if not self.client:
            return

        models = ["sonnet", "opus", "haiku"]
        current_idx = models.index(self.current_model) if self.current_model in models else 0
        next_idx = (current_idx + 1) % len(models)
        self.current_model = models[next_idx]

        await self.client.set_model(self.current_model)
        self.query_one("#model-display", Label).update(self.current_model)

        chat = self.query_one("#chat-container", ChatContainer)
        chat.add_message("system", f"Switched to **{self.current_model}**")

    def action_toggle_hooks(self) -> None:
        """Toggle hook output visibility."""
        self.show_hooks = not self.show_hooks
        chat = self.query_one("#chat-container", ChatContainer)
        state = "enabled" if self.show_hooks else "disabled"
        chat.add_message("system", f"Hook output **{state}**")

    async def on_unmount(self) -> None:
        """Clean up on exit."""
        if self.client:
            await self.client.disconnect()


def main() -> None:
    """Entry point for cameron-code TUI."""
    app = CameronCodeApp()
    app.run()


if __name__ == "__main__":
    main()
