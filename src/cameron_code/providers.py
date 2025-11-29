"""Provider configuration utilities for Cameron Code.

The Claude Agent SDK is a thin wrapper around the Claude Code CLI. Provider support
is determined by CLI capabilities, not the SDK itself.

Currently, the SDK/CLI supports:
- Native Anthropic API (default)

The SDK provides escape hatches via `env` and `extra_args` in ClaudeAgentOptions
for any future CLI provider options.
"""

from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""

    name: str
    display_name: str
    env_vars: dict[str, str]
    extra_args: list[str]
    description: str
    supported: bool = True


# Known provider configurations
# Note: These are theoretical - actual support depends on CLI capabilities
PROVIDERS: dict[str, ProviderConfig] = {
    "anthropic": ProviderConfig(
        name="anthropic",
        display_name="Anthropic",
        env_vars={},
        extra_args=[],
        description="Native Anthropic API (default)",
        supported=True,
    ),
    "bedrock": ProviderConfig(
        name="bedrock",
        display_name="AWS Bedrock",
        env_vars={
            "AWS_REGION": "",
            "AWS_ACCESS_KEY_ID": "",
            "AWS_SECRET_ACCESS_KEY": "",
        },
        extra_args=[],
        description="AWS Bedrock Claude models (requires CLI support)",
        supported=False,
    ),
    "vertex": ProviderConfig(
        name="vertex",
        display_name="Google Vertex AI",
        env_vars={
            "GOOGLE_CLOUD_PROJECT": "",
            "GOOGLE_CLOUD_REGION": "",
        },
        extra_args=[],
        description="Google Vertex AI Claude models (requires CLI support)",
        supported=False,
    ),
}


def get_provider(name: str) -> ProviderConfig | None:
    """Get a provider configuration by name."""
    return PROVIDERS.get(name)


def list_providers(include_unsupported: bool = False) -> list[ProviderConfig]:
    """List available providers."""
    if include_unsupported:
        return list(PROVIDERS.values())
    return [p for p in PROVIDERS.values() if p.supported]


def apply_provider_config(
    options: ClaudeAgentOptions,
    provider: ProviderConfig | str,
    env_overrides: dict[str, str] | None = None,
) -> ClaudeAgentOptions:
    """Apply provider configuration to ClaudeAgentOptions.

    Args:
        options: Base options to modify
        provider: Provider config or name
        env_overrides: Override specific environment variables

    Returns:
        Modified options with provider configuration
    """
    if isinstance(provider, str):
        config = get_provider(provider)
        if not config:
            raise ValueError(f"Unknown provider: {provider}")
    else:
        config = provider

    # Merge environment variables
    env = dict(options.env or {})
    env.update(config.env_vars)
    if env_overrides:
        env.update(env_overrides)

    # Merge extra args
    extra_args = list(options.extra_args or [])
    extra_args.extend(config.extra_args)

    # Create new options with provider config
    return ClaudeAgentOptions(
        model=options.model,
        max_turns=options.max_turns,
        allowed_tools=options.allowed_tools,
        permission_mode=options.permission_mode,
        cwd=options.cwd,
        env=env if env else None,
        extra_args=extra_args if extra_args else None,
        setting_sources=options.setting_sources,
        hooks=options.hooks,
        mcp_servers=options.mcp_servers,
        can_use_tool=options.can_use_tool,
    )


def create_options_for_provider(
    provider_name: str,
    *,
    cwd: str | None = None,
    setting_sources: list[str] | None = None,
    env_overrides: dict[str, str] | None = None,
    **kwargs: Any,
) -> ClaudeAgentOptions:
    """Create ClaudeAgentOptions configured for a specific provider.

    Args:
        provider_name: Name of the provider (anthropic, bedrock, vertex)
        cwd: Working directory
        setting_sources: Setting sources to load (default: ["project"])
        env_overrides: Override provider environment variables
        **kwargs: Additional options to pass through

    Returns:
        Configured ClaudeAgentOptions

    Example:
        options = create_options_for_provider(
            "anthropic",
            cwd="/path/to/project",
            setting_sources=["user", "project"],
        )
    """
    provider = get_provider(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")

    if not provider.supported:
        raise ValueError(
            f"Provider '{provider_name}' is not currently supported. "
            "Provider support depends on Claude Code CLI capabilities."
        )

    base_options = ClaudeAgentOptions(
        cwd=cwd,
        setting_sources=setting_sources if setting_sources is not None else ["project"],
        **kwargs,
    )

    return apply_provider_config(base_options, provider, env_overrides)


def get_current_provider_info() -> dict[str, Any]:
    """Get information about currently active provider.

    Returns dict with:
        - name: Provider name
        - display_name: Human-readable name
        - description: Provider description
        - env_required: Required environment variables
    """
    # Currently only Anthropic is supported
    provider = PROVIDERS["anthropic"]
    return {
        "name": provider.name,
        "display_name": provider.display_name,
        "description": provider.description,
        "env_required": list(provider.env_vars.keys()),
        "supported": provider.supported,
    }
