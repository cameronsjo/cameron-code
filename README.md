# cameron-code

Tinkering with the [Claude Code SDK](https://github.com/anthropics/claude-code-sdk-python) to see what's possible.

## What's This?

A playground for experimenting with Claude Code's programmatic interface. Features:

- **Custom TUI** - A simple terminal interface built with Textual
- **Custom MCP Tools** - In-process Python tools (search, time, etc.)
- **Hooks & Permissions** - Pre/post tool execution callbacks
- **Audit Logging** - Track everything Claude does
- **Slash Commands** - Full support via `setting_sources`

## Quick Start

```bash
# Install
uv sync

# Run the TUI
uv run cameron-code

# Or run tests
uv run pytest tests/ -v
```

## Experiments

Inspired by [tweakcc](https://github.com/cameronsjo/tweakcc), exploring:

- [ ] Custom thinking verbs/spinners
- [ ] Theme customization
- [ ] Tool result formatting
- [ ] Session management
- [ ] Context visualization

## Key Discovery

The SDK defaults to `setting_sources=None` which disables all settings (including slash commands). Fix:

```python
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Enable ~/.claude/ and .claude/
    cwd="/path/to/project",
)
```

## License

MIT - do whatever
