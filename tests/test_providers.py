"""Tests for provider configuration utilities."""

import pytest
from claude_agent_sdk import ClaudeAgentOptions

from cameron_code.providers import (
    ProviderConfig,
    PROVIDERS,
    get_provider,
    list_providers,
    apply_provider_config,
    create_options_for_provider,
    get_current_provider_info,
)


def test_providers_registry_has_anthropic() -> None:
    """Verify anthropic provider is registered and supported."""
    assert "anthropic" in PROVIDERS
    assert PROVIDERS["anthropic"].supported is True


def test_providers_registry_has_unsupported() -> None:
    """Verify unsupported providers are registered but marked."""
    assert "bedrock" in PROVIDERS
    assert PROVIDERS["bedrock"].supported is False

    assert "vertex" in PROVIDERS
    assert PROVIDERS["vertex"].supported is False


def test_get_provider_valid() -> None:
    """Test getting a valid provider."""
    provider = get_provider("anthropic")
    assert provider is not None
    assert provider.name == "anthropic"
    assert provider.display_name == "Anthropic"


def test_get_provider_invalid() -> None:
    """Test getting an invalid provider returns None."""
    provider = get_provider("nonexistent")
    assert provider is None


def test_list_providers_supported_only() -> None:
    """Test listing only supported providers."""
    providers = list_providers(include_unsupported=False)
    assert len(providers) >= 1
    assert all(p.supported for p in providers)
    assert any(p.name == "anthropic" for p in providers)


def test_list_providers_all() -> None:
    """Test listing all providers including unsupported."""
    providers = list_providers(include_unsupported=True)
    assert len(providers) >= 3
    names = [p.name for p in providers]
    assert "anthropic" in names
    assert "bedrock" in names
    assert "vertex" in names


def test_apply_provider_config_anthropic() -> None:
    """Test applying anthropic provider config."""
    base = ClaudeAgentOptions(cwd="/test", max_turns=5)
    result = apply_provider_config(base, "anthropic")

    assert result.cwd == "/test"
    assert result.max_turns == 5


def test_apply_provider_config_with_env_overrides() -> None:
    """Test applying provider config with environment overrides."""
    base = ClaudeAgentOptions(cwd="/test")
    result = apply_provider_config(
        base,
        "anthropic",
        env_overrides={"CUSTOM_VAR": "value"},
    )

    assert result.env is not None
    assert result.env["CUSTOM_VAR"] == "value"


def test_apply_provider_config_invalid_provider() -> None:
    """Test applying config for invalid provider raises error."""
    base = ClaudeAgentOptions()
    with pytest.raises(ValueError, match="Unknown provider"):
        apply_provider_config(base, "nonexistent")


def test_create_options_for_provider_anthropic() -> None:
    """Test creating options for anthropic provider."""
    options = create_options_for_provider(
        "anthropic",
        cwd="/test",
        max_turns=10,
    )

    assert options.cwd == "/test"
    assert options.max_turns == 10
    assert options.setting_sources == ["project"]


def test_create_options_for_provider_unsupported() -> None:
    """Test creating options for unsupported provider raises error."""
    with pytest.raises(ValueError, match="not currently supported"):
        create_options_for_provider("bedrock")


def test_create_options_for_provider_invalid() -> None:
    """Test creating options for invalid provider raises error."""
    with pytest.raises(ValueError, match="Unknown provider"):
        create_options_for_provider("nonexistent")


def test_get_current_provider_info() -> None:
    """Test getting current provider info."""
    info = get_current_provider_info()

    assert info["name"] == "anthropic"
    assert info["display_name"] == "Anthropic"
    assert info["supported"] is True
    assert isinstance(info["env_required"], list)
