"""Cameron Code TUI - A simple terminal interface for Claude Code SDK."""

import asyncio
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
    OptionList,
)
from textual.widgets.option_list import Option
from textual.suggester import Suggester

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
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


class SlashCommandSuggester(Suggester):
    """Suggester for slash commands."""

    def __init__(self, commands: list[dict]) -> None:
        super().__init__(use_cache=False, case_sensitive=False)
        self.commands = commands
        self._command_names = [f"/{c['name']}" for c in commands]

    async def get_suggestion(self, value: str) -> str | None:
        """Get autocomplete suggestion for slash commands."""
        if not value.startswith("/"):
            return None

        value_lower = value.lower()
        for cmd in self._command_names:
            if cmd.lower().startswith(value_lower) and cmd.lower() != value_lower:
                return cmd
        return None


class CommandPalette(Static):
    """Command palette showing available slash commands."""

    def __init__(self, commands: list[dict], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.commands = commands

    def compose(self) -> ComposeResult:
        yield Label("[bold]Available Commands[/bold]", classes="palette-header")
        options = []
        for cmd in self.commands:
            name = cmd.get("name", "")
            desc = cmd.get("description", "")[:50]
            options.append(Option(f"/{name} - {desc}"))
        yield OptionList(*options, id="command-list")


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

    #main-container {
        height: 1fr;
    }

    #chat-container {
        height: 1fr;
        padding: 1;
        border: solid $primary;
    }

    #command-palette {
        width: 40;
        height: 100%;
        dock: right;
        background: $surface-darken-2;
        border-left: solid $primary;
        padding: 1;
        display: none;
    }

    #command-palette.visible {
        display: block;
    }

    .palette-header {
        margin-bottom: 1;
        text-style: bold;
        color: $primary;
    }

    #command-list {
        height: 1fr;
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

    #provider-display {
        dock: right;
        width: auto;
        margin-right: 2;
        color: $accent;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+m", "switch_model", "Model"),
        Binding("ctrl+h", "toggle_hooks", "Hooks"),
        Binding("ctrl+p", "toggle_palette", "Commands"),
        Binding("tab", "complete", "Complete", show=False),
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
        self.available_commands: list[dict] = []
        self.palette_visible = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            yield ChatContainer(id="chat-container")
            yield CommandPalette([], id="command-palette")
        with Container(id="input-container"):
            yield Input(placeholder="Ask Cameron anything... (type / for commands)", id="prompt-input")
        with Horizontal(id="status-bar"):
            yield Label("Ready", id="status-label")
            yield Label("", id="turns-display")
            yield Label("anthropic", id="provider-display")
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
            "**Keybindings:**\n"
            "- `Ctrl+P` - Toggle command palette\n"
            "- `Ctrl+M` - Switch model (sonnet/opus/haiku)\n"
            "- `Ctrl+H` - Toggle hook output\n"
            "- `Ctrl+L` - Clear chat\n"
            "- `Tab` - Autocomplete slash commands\n"
            "- `Esc` - Cancel operation\n\n"
            "Type `/` to see command suggestions!"
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

        # Get available commands and set up autocomplete
        info = await self.client.get_server_info()
        if info:
            self.available_commands = info.get("commands", [])
            if self.available_commands:
                # Update input with suggester
                input_widget = self.query_one("#prompt-input", Input)
                input_widget.suggester = SlashCommandSuggester(self.available_commands)

                # Update command palette
                palette = self.query_one("#command-palette", CommandPalette)
                palette.commands = self.available_commands
                palette.refresh()

                cmd_list = ", ".join(f"`/{c['name']}`" for c in self.available_commands[:5])
                chat = self.query_one("#chat-container", ChatContainer)
                chat.add_message("system", f"Commands: {cmd_list}... (Ctrl+P for all)")

    def _update_status(self, text: str) -> None:
        self.query_one("#status-label", Label).update(text)

    def _update_cost(self) -> None:
        self.query_one("#cost-display", Label).update(f"${self.total_cost:.4f}")

    def _update_turns(self) -> None:
        self.query_one("#turns-display", Label).update(f"turns: {self.total_turns}")

    def _show_thinking(self, tool_name: str | None = None) -> None:
        self._hide_thinking()
        self._thinking_indicator = ThinkingIndicator(tool_name=tool_name)
        chat = self.query_one("#chat-container", ChatContainer)
        chat.mount(self._thinking_indicator)
        chat.scroll_end(animate=False)

    def _hide_thinking(self) -> None:
        if self._thinking_indicator:
            self._thinking_indicator.remove()
            self._thinking_indicator = None

    @on(Input.Changed, "#prompt-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        """Show command hints when typing /."""
        # Could add inline hints here
        pass

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

    @on(OptionList.OptionSelected, "#command-list")
    def on_command_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle command selection from palette."""
        # Extract command name from "/{name} - {desc}"
        option_text = str(event.option.prompt)
        cmd_name = option_text.split(" - ")[0]

        input_widget = self.query_one("#prompt-input", Input)
        input_widget.value = cmd_name + " "
        input_widget.focus()

        # Hide palette
        self.action_toggle_palette()

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
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            current_text += block.text
                        elif isinstance(block, ToolUseBlock):
                            if current_text.strip():
                                self._hide_thinking()
                                chat.add_message("assistant", current_text)
                                current_text = ""
                            chat.add_message("tool", f"**{block.name}**")
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

    def action_toggle_palette(self) -> None:
        """Toggle command palette visibility."""
        palette = self.query_one("#command-palette", CommandPalette)
        self.palette_visible = not self.palette_visible
        if self.palette_visible:
            palette.add_class("visible")
            # Refresh with current commands
            palette.remove_children()
            palette.mount(Label("[bold]Available Commands[/bold]", classes="palette-header"))
            options = []
            for cmd in self.available_commands:
                name = cmd.get("name", "")
                desc = cmd.get("description", "")[:40]
                options.append(Option(f"/{name} - {desc}"))
            palette.mount(OptionList(*options, id="command-list"))
        else:
            palette.remove_class("visible")

    def action_complete(self) -> None:
        """Accept autocomplete suggestion."""
        input_widget = self.query_one("#prompt-input", Input)
        # Textual's Input handles Tab for suggestion acceptance by default
        pass

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
