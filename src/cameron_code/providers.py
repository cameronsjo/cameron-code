"""Provider configuration utilities for Cameron Code.

Claude Code supports alternative providers via ANTHROPIC_BASE_URL environment variable.
This allows connecting to any API that implements Anthropic's message format.

Officially supported:
- Native Anthropic API (default)
- AWS Bedrock (CLAUDE_CODE_USE_BEDROCK=1)
- Google Vertex AI (CLAUDE_CODE_USE_VERTEX=1)

Community-validated providers (via ANTHROPIC_BASE_URL):
- DeepSeek (https://api.deepseek.com/anthropic)
- GLM/Z.AI (https://api.z.ai/api/anthropic)
- OpenRouter (via proxy)
- Ollama (via proxy)
- Any OpenAI-compatible API (via LiteLLM proxy)

See: https://github.com/musistudio/claude-code-router for intelligent routing.
"""

from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""

    name: str
    display_name: str
    base_url: str | None
    env_vars: dict[str, str] = field(default_factory=dict)
    default_model: str | None = None
    description: str = ""
    official: bool = False


# Known provider configurations
PROVIDERS: dict[str, ProviderConfig] = {
    # Official providers
    "anthropic": ProviderConfig(
        name="anthropic",
        display_name="Anthropic",
        base_url=None,  # Uses default
        env_vars={},
        default_model=None,  # Uses CLI default
        description="Native Anthropic API (default)",
        official=True,
    ),
    "bedrock": ProviderConfig(
        name="bedrock",
        display_name="AWS Bedrock",
        base_url=None,
        env_vars={
            "CLAUDE_CODE_USE_BEDROCK": "1",
        },
        default_model=None,
        description="AWS Bedrock Claude models",
        official=True,
    ),
    "vertex": ProviderConfig(
        name="vertex",
        display_name="Google Vertex AI",
        base_url=None,
        env_vars={
            "CLAUDE_CODE_USE_VERTEX": "1",
        },
        default_model=None,
        description="Google Vertex AI Claude models",
        official=True,
    ),
    # Community-validated providers
    "deepseek": ProviderConfig(
        name="deepseek",
        display_name="DeepSeek",
        base_url="https://api.deepseek.com/anthropic",
        env_vars={},
        default_model="deepseek-chat",
        description="DeepSeek API with Anthropic compatibility",
        official=False,
    ),
    "deepseek-reasoner": ProviderConfig(
        name="deepseek-reasoner",
        display_name="DeepSeek Reasoner",
        base_url="https://api.deepseek.com/anthropic",
        env_vars={},
        default_model="deepseek-reasoner",
        description="DeepSeek R1 reasoning model",
        official=False,
    ),
    "glm": ProviderConfig(
        name="glm",
        display_name="GLM (Z.AI)",
        base_url="https://api.z.ai/api/anthropic",
        env_vars={},
        default_model="glm-4.5-air",
        description="GLM models via Z.AI Anthropic-compatible API",
        official=False,
    ),
    "openrouter": ProviderConfig(
        name="openrouter",
        display_name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        env_vars={},
        default_model="anthropic/claude-3.5-sonnet",
        description="OpenRouter aggregator (requires proxy like claude-code-router)",
        official=False,
    ),
}


def get_provider(name: str) -> ProviderConfig | None:
    """Get a provider configuration by name."""
    return PROVIDERS.get(name)


def list_providers(*, official_only: bool = False) -> list[ProviderConfig]:
    """List available providers.

    Args:
        official_only: If True, only return officially supported providers
    """
    if official_only:
        return [p for p in PROVIDERS.values() if p.official]
    return list(PROVIDERS.values())


def create_custom_provider(
    name: str,
    base_url: str,
    *,
    display_name: str | None = None,
    api_key_env: str = "ANTHROPIC_AUTH_TOKEN",
    default_model: str | None = None,
    description: str = "",
) -> ProviderConfig:
    """Create a custom provider configuration.

    Args:
        name: Internal name for the provider
        base_url: API base URL (ANTHROPIC_BASE_URL)
        display_name: Human-readable name
        api_key_env: Environment variable name for API key
        default_model: Default model to use
        description: Provider description

    Returns:
        ProviderConfig for the custom provider

    Example:
        custom = create_custom_provider(
            "my-proxy",
            "http://localhost:8080",
            default_model="gpt-4",
            description="Local LiteLLM proxy",
        )
    """
    return ProviderConfig(
        name=name,
        display_name=display_name or name,
        base_url=base_url,
        env_vars={},
        default_model=default_model,
        description=description,
        official=False,
    )


def apply_provider_config(
    options: ClaudeAgentOptions,
    provider: ProviderConfig | str,
    *,
    api_key: str | None = None,
    model_override: str | None = None,
    env_overrides: dict[str, str] | None = None,
) -> ClaudeAgentOptions:
    """Apply provider configuration to ClaudeAgentOptions.

    Args:
        options: Base options to modify
        provider: Provider config or name
        api_key: API key for the provider (sets ANTHROPIC_AUTH_TOKEN)
        model_override: Override the default model
        env_overrides: Additional environment variable overrides

    Returns:
        Modified options with provider configuration
    """
    if isinstance(provider, str):
        config = get_provider(provider)
        if not config:
            raise ValueError(f"Unknown provider: {provider}")
    else:
        config = provider

    # Build environment variables
    env = dict(options.env or {})
    env.update(config.env_vars)

    # Set base URL if provider specifies one
    if config.base_url:
        env["ANTHROPIC_BASE_URL"] = config.base_url

    # Set API key if provided
    if api_key:
        env["ANTHROPIC_AUTH_TOKEN"] = api_key

    # Set model if provider has default or override specified
    model = model_override or config.default_model
    if model:
        env["ANTHROPIC_MODEL"] = model

    # Apply any additional overrides
    if env_overrides:
        env.update(env_overrides)

    # Create new options with provider config
    return ClaudeAgentOptions(
        model=options.model,
        max_turns=options.max_turns,
        allowed_tools=options.allowed_tools,
        permission_mode=options.permission_mode,
        cwd=options.cwd,
        env=env if env else None,
        extra_args=options.extra_args,
        setting_sources=options.setting_sources,
        hooks=options.hooks,
        mcp_servers=options.mcp_servers,
        can_use_tool=options.can_use_tool,
    )


def create_options_for_provider(
    provider_name: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    cwd: str | None = None,
    setting_sources: list[str] | None = None,
    env_overrides: dict[str, str] | None = None,
    **kwargs: Any,
) -> ClaudeAgentOptions:
    """Create ClaudeAgentOptions configured for a specific provider.

    Args:
        provider_name: Name of the provider (anthropic, deepseek, glm, etc.)
        api_key: API key for the provider
        model: Model to use (overrides provider default)
        cwd: Working directory
        setting_sources: Setting sources to load (default: ["project"])
        env_overrides: Override provider environment variables
        **kwargs: Additional options to pass through

    Returns:
        Configured ClaudeAgentOptions

    Example:
        # Use DeepSeek
        options = create_options_for_provider(
            "deepseek",
            api_key="sk-xxx",
            cwd="/path/to/project",
        )

        # Use DeepSeek Reasoner for complex tasks
        options = create_options_for_provider(
            "deepseek-reasoner",
            api_key="sk-xxx",
        )

        # Use GLM
        options = create_options_for_provider(
            "glm",
            api_key="your-zai-key",
            model="glm-4.5-air",
        )
    """
    provider = get_provider(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")

    base_options = ClaudeAgentOptions(
        cwd=cwd,
        setting_sources=setting_sources if setting_sources is not None else ["project"],
        **kwargs,
    )

    return apply_provider_config(
        base_options,
        provider,
        api_key=api_key,
        model_override=model,
        env_overrides=env_overrides,
    )


def get_provider_env_example(provider_name: str) -> str:
    """Get example environment variable setup for a provider.

    Args:
        provider_name: Name of the provider

    Returns:
        Shell export commands for the provider
    """
    provider = get_provider(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")

    lines = [f"# {provider.display_name} configuration"]

    if provider.base_url:
        lines.append(f'export ANTHROPIC_BASE_URL="{provider.base_url}"')

    lines.append('export ANTHROPIC_AUTH_TOKEN="your-api-key-here"')

    if provider.default_model:
        lines.append(f'export ANTHROPIC_MODEL="{provider.default_model}"')

    for key, value in provider.env_vars.items():
        lines.append(f'export {key}="{value}"')

    return "\n".join(lines)


def get_current_provider_info() -> dict[str, Any]:
    """Get information about currently active provider based on environment.

    Checks environment variables to determine which provider is configured.

    Returns dict with:
        - name: Provider name
        - display_name: Human-readable name
        - description: Provider description
        - base_url: Configured base URL (if any)
        - model: Configured model (if any)
    """
    import os

    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    model = os.environ.get("ANTHROPIC_MODEL")
    use_bedrock = os.environ.get("CLAUDE_CODE_USE_BEDROCK")
    use_vertex = os.environ.get("CLAUDE_CODE_USE_VERTEX")

    # Check official providers first
    if use_bedrock:
        provider = PROVIDERS["bedrock"]
    elif use_vertex:
        provider = PROVIDERS["vertex"]
    elif base_url:
        # Try to match base URL to known provider
        for p in PROVIDERS.values():
            if p.base_url and p.base_url in base_url:
                provider = p
                break
        else:
            # Custom provider
            return {
                "name": "custom",
                "display_name": "Custom Provider",
                "description": f"Custom API at {base_url}",
                "base_url": base_url,
                "model": model,
                "official": False,
            }
    else:
        provider = PROVIDERS["anthropic"]

    return {
        "name": provider.name,
        "display_name": provider.display_name,
        "description": provider.description,
        "base_url": base_url or provider.base_url,
        "model": model or provider.default_model,
        "official": provider.official,
    }
