# cameron-code

Tinkering with the [Claude Code SDK](https://github.com/anthropics/claude-code-sdk-python) to see what's possible.

## What's This?

A playground for experimenting with Claude Code's programmatic interface. Features:

- **Custom TUI** - A simple terminal interface built with Textual
- **Custom MCP Tools** - In-process Python tools (search, time, etc.)
- **Hooks & Permissions** - Pre/post tool execution callbacks
- **Audit Logging** - Track everything Claude does
- **Slash Commands** - Full support via `setting_sources`
- **Provider Utilities** - Connect to DeepSeek, GLM, and other alternative providers

## Quick Start

```bash
# Install
uv sync

# Run the TUI
uv run cameron-code

# Or run tests
uv run pytest tests/ -v
```

## Alternative Providers

Claude Code supports alternative providers via the `ANTHROPIC_BASE_URL` environment variable. This allows connecting to any API that implements Anthropic's message format.

### Official Providers

| Provider | Configuration | Notes |
|----------|--------------|-------|
| Anthropic | Default | Native API |
| AWS Bedrock | `CLAUDE_CODE_USE_BEDROCK=1` | Requires AWS credentials |
| Google Vertex AI | `CLAUDE_CODE_USE_VERTEX=1` | Requires GCP credentials |

### Community Providers

These providers have Anthropic-compatible API endpoints:

| Provider | Base URL | Default Model |
|----------|----------|---------------|
| DeepSeek | `https://api.deepseek.com/anthropic` | `deepseek-chat` |
| DeepSeek Reasoner | `https://api.deepseek.com/anthropic` | `deepseek-reasoner` |
| GLM (Z.AI) | `https://api.z.ai/api/anthropic` | `glm-4.5-air` |
| OpenRouter | `https://openrouter.ai/api/v1` | Requires proxy |

### Usage

#### Environment Variables (Direct)

```bash
# DeepSeek
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="your-deepseek-api-key"
export ANTHROPIC_MODEL="deepseek-chat"

# GLM
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_AUTH_TOKEN="your-zai-api-key"
export ANTHROPIC_MODEL="glm-4.5-air"
```

#### Python API

```python
from cameron_code import create_options_for_provider

# Use DeepSeek
options = create_options_for_provider(
    "deepseek",
    api_key="sk-xxx",
    cwd="/path/to/project",
)

# Use DeepSeek Reasoner for complex reasoning tasks
options = create_options_for_provider(
    "deepseek-reasoner",
    api_key="sk-xxx",
)

# Use GLM
options = create_options_for_provider(
    "glm",
    api_key="your-zai-key",
)
```

#### Custom Providers

```python
from cameron_code import create_custom_provider, apply_provider_config
from claude_agent_sdk import ClaudeAgentOptions

# Create a custom provider (e.g., local LiteLLM proxy)
litellm = create_custom_provider(
    "litellm",
    "http://localhost:4000",
    default_model="gpt-4",
    description="Local LiteLLM proxy",
)

# Apply to options
base_options = ClaudeAgentOptions(cwd="/path/to/project")
options = apply_provider_config(base_options, litellm, api_key="your-key")
```

#### Get Provider Examples

```python
from cameron_code import get_provider_env_example

# Print shell export commands for a provider
print(get_provider_env_example("deepseek"))
# Output:
# # DeepSeek configuration
# export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
# export ANTHROPIC_AUTH_TOKEN="your-api-key-here"
# export ANTHROPIC_MODEL="deepseek-chat"
```

### Advanced: Intelligent Routing

For routing different requests to different providers (e.g., cheap model for simple tasks, reasoning model for complex ones), check out [claude-code-router](https://github.com/musistudio/claude-code-router).

## Key Discoveries

### Slash Commands Need `setting_sources`

The SDK defaults to `setting_sources=None` which disables all settings (including slash commands). Fix:

```python
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Enable ~/.claude/ and .claude/
    cwd="/path/to/project",
)
```

### SDK Architecture

The Claude Agent SDK is a thin wrapper around the Claude Code CLI:

```
Your Code → SDK → Subprocess (claude CLI) → Anthropic API (or alternative)
                      ↑
              JSON line protocol
```

The SDK provides:

- Bidirectional streaming via subprocess
- Hook callbacks (PreToolUse, PostToolUse, etc.)
- In-process MCP servers
- Permission callbacks

## Experiments

Inspired by [tweakcc](https://github.com/cameronsjo/tweakcc), exploring:

- [x] Custom thinking verbs/spinners
- [x] Slash command autocomplete
- [x] Provider switching
- [ ] Theme customization
- [ ] Tool result formatting
- [ ] Session management
- [ ] Context visualization

## TUI Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+P` | Toggle command palette |
| `Ctrl+M` | Switch model (sonnet/opus/haiku) |
| `Ctrl+H` | Toggle hook output |
| `Ctrl+L` | Clear chat |
| `Tab` | Autocomplete slash commands |
| `Esc` | Cancel operation |

## License

MIT - do whatever
