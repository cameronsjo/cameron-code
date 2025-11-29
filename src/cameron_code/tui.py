"""Cameron Code TUI - A simple terminal interface for Claude Code SDK."""

import asyncio
from datetime import datetime
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Static,
    LoadingIndicator,
)
from textual.message import Message as TextualMessage

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    UserMessage,
    TextBlock,
    ToolUseBlock,
    ThinkingBlock,
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
]


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
        }.get(self.role, self.role)

        role_class = f"role-{self.role}"
        yield Label(f"[bold]{role_display}[/bold]", classes=f"message-role {role_class}")
        yield Markdown(self.content, classes="message-content")


class ThinkingIndicator(Static):
    """Animated thinking indicator with custom verbs."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.verb_index = 0

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()
        yield Label(THINKING_VERBS[0], id="thinking-verb")

    def on_mount(self) -> None:
        self.set_interval(0.8, self._rotate_verb)

    def _rotate_verb(self) -> None:
        self.verb_index = (self.verb_index + 1) % len(THINKING_VERBS)
        verb_label = self.query_one("#thinking-verb", Label)
        verb_label.update(THINKING_VERBS[self.verb_index])


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
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.client: ClaudeSDKClient | None = None
        self.total_cost: float = 0.0
        self.is_processing = False
        self._thinking_indicator: ThinkingIndicator | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ChatContainer(id="chat-container")
        with Container(id="input-container"):
            yield Input(placeholder="Ask Cameron anything... (or /command)", id="prompt-input")
        with Horizontal(id="status-bar"):
            yield Label("Ready", id="status-label")
            yield Label("$0.0000", id="cost-display")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the Claude client on mount."""
        self.query_one("#prompt-input", Input).focus()

        # Welcome message
        chat = self.query_one("#chat-container", ChatContainer)
        chat.add_message(
            "system",
            "Welcome to **Cameron Code**! 🎉\n\n"
            "A custom Claude Code TUI with:\n"
            "- Custom MCP tools (`cameron_search`, `cameron_time`)\n"
            "- Audit logging & hooks\n"
            "- Slash command support\n\n"
            "Type a message or use `/commands` to see available slash commands."
        )

        # Initialize client
        await self._init_client()

    async def _init_client(self) -> None:
        """Initialize the Claude SDK client."""
        cameron_server = create_sdk_mcp_server(
            name="cameron-tools",
            tools=[cameron_search, cameron_time],
        )

        options = ClaudeAgentOptions(
            mcp_servers={"cameron": cameron_server},
            setting_sources=["user", "project"],
            cwd=".",
            max_turns=20,
        )

        self.client = ClaudeSDKClient(options)
        await self.client.connect()

        # Show available commands
        info = await self.client.get_server_info()
        if info:
            commands = info.get("commands", [])
            if commands:
                cmd_list = ", ".join(f"`/{c['name']}`" for c in commands[:10])
                chat = self.query_one("#chat-container", ChatContainer)
                chat.add_message("system", f"Available commands: {cmd_list}")

    def _update_status(self, text: str) -> None:
        self.query_one("#status-label", Label).update(text)

    def _update_cost(self) -> None:
        self.query_one("#cost-display", Label).update(f"${self.total_cost:.4f}")

    def _show_thinking(self) -> None:
        if not self._thinking_indicator:
            self._thinking_indicator = ThinkingIndicator()
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

        # Clear input
        event.input.value = ""

        # Add user message
        chat = self.query_one("#chat-container", ChatContainer)
        chat.add_message("user", prompt)

        # Process with Claude
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
            async for msg in self.client.receive_response():
                self._hide_thinking()

                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            current_text += block.text
                        elif isinstance(block, ToolUseBlock):
                            chat.add_message("tool", f"Using **{block.name}**...")
                        elif isinstance(block, ThinkingBlock):
                            # Show thinking in muted style
                            if block.thinking:
                                thinking_preview = block.thinking[:200]
                                if len(block.thinking) > 200:
                                    thinking_preview += "..."
                                chat.add_message("thinking", thinking_preview)

                elif isinstance(msg, ResultMessage):
                    if current_text:
                        chat.add_message("assistant", current_text)
                        current_text = ""

                    if msg.total_cost_usd:
                        self.total_cost += msg.total_cost_usd
                        self._update_cost()

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
        chat.add_message("system", "Chat cleared. Start fresh!")

    async def action_cancel(self) -> None:
        """Cancel current operation."""
        if self.client and self.is_processing:
            await self.client.interrupt()
            self._hide_thinking()
            self._update_status("Cancelled")
            self.is_processing = False

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
