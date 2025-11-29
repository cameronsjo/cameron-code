"""Tests for provider configuration utilities."""

import os
import pytest
from claude_agent_sdk import ClaudeAgentOptions

from cameron_code.providers import (
    ProviderConfig,
    PROVIDERS,
    get_provider,
    list_providers,
    create_custom_provider,
    apply_provider_config,
    create_options_for_provider,
    get_provider_env_example,
    get_current_provider_info,
)


class TestProviderRegistry:
    """Tests for provider registry."""

    def test_has_official_providers(self) -> None:
        """Verify official providers are registered."""
        assert "anthropic" in PROVIDERS
        assert "bedrock" in PROVIDERS
        assert "vertex" in PROVIDERS

        assert PROVIDERS["anthropic"].official is True
        assert PROVIDERS["bedrock"].official is True
        assert PROVIDERS["vertex"].official is True

    def test_has_community_providers(self) -> None:
        """Verify community providers are registered."""
        assert "deepseek" in PROVIDERS
        assert "deepseek-reasoner" in PROVIDERS
        assert "glm" in PROVIDERS

        assert PROVIDERS["deepseek"].official is False
        assert PROVIDERS["glm"].official is False

    def test_deepseek_has_correct_base_url(self) -> None:
        """Verify DeepSeek provider has correct configuration."""
        deepseek = PROVIDERS["deepseek"]
        assert deepseek.base_url == "https://api.deepseek.com/anthropic"
        assert deepseek.default_model == "deepseek-chat"

    def test_glm_has_correct_base_url(self) -> None:
        """Verify GLM provider has correct configuration."""
        glm = PROVIDERS["glm"]
        assert glm.base_url == "https://api.z.ai/api/anthropic"
        assert glm.default_model == "glm-4.5-air"


class TestGetProvider:
    """Tests for get_provider function."""

    def test_valid_provider(self) -> None:
        """Test getting a valid provider."""
        provider = get_provider("anthropic")
        assert provider is not None
        assert provider.name == "anthropic"

        provider = get_provider("deepseek")
        assert provider is not None
        assert provider.name == "deepseek"

    def test_invalid_provider(self) -> None:
        """Test getting an invalid provider returns None."""
        provider = get_provider("nonexistent")
        assert provider is None


class TestListProviders:
    """Tests for list_providers function."""

    def test_list_all(self) -> None:
        """Test listing all providers."""
        providers = list_providers()
        assert len(providers) >= 6
        names = [p.name for p in providers]
        assert "anthropic" in names
        assert "deepseek" in names
        assert "glm" in names

    def test_list_official_only(self) -> None:
        """Test listing only official providers."""
        providers = list_providers(official_only=True)
        assert len(providers) == 3
        assert all(p.official for p in providers)
        names = [p.name for p in providers]
        assert "anthropic" in names
        assert "bedrock" in names
        assert "vertex" in names


class TestCreateCustomProvider:
    """Tests for create_custom_provider function."""

    def test_create_basic(self) -> None:
        """Test creating a basic custom provider."""
        provider = create_custom_provider(
            "my-proxy",
            "http://localhost:8080",
        )
        assert provider.name == "my-proxy"
        assert provider.base_url == "http://localhost:8080"
        assert provider.official is False

    def test_create_with_options(self) -> None:
        """Test creating custom provider with all options."""
        provider = create_custom_provider(
            "litellm",
            "http://localhost:4000",
            display_name="LiteLLM Proxy",
            default_model="gpt-4",
            description="Local LiteLLM proxy",
        )
        assert provider.name == "litellm"
        assert provider.display_name == "LiteLLM Proxy"
        assert provider.default_model == "gpt-4"
        assert provider.description == "Local LiteLLM proxy"


class TestApplyProviderConfig:
    """Tests for apply_provider_config function."""

    def test_apply_anthropic(self) -> None:
        """Test applying anthropic provider config."""
        base = ClaudeAgentOptions(cwd="/test", max_turns=5)
        result = apply_provider_config(base, "anthropic")

        assert result.cwd == "/test"
        assert result.max_turns == 5

    def test_apply_deepseek(self) -> None:
        """Test applying deepseek provider config."""
        base = ClaudeAgentOptions(cwd="/test")
        result = apply_provider_config(base, "deepseek", api_key="sk-test")

        assert result.env is not None
        assert result.env["ANTHROPIC_BASE_URL"] == "https://api.deepseek.com/anthropic"
        assert result.env["ANTHROPIC_AUTH_TOKEN"] == "sk-test"
        assert result.env["ANTHROPIC_MODEL"] == "deepseek-chat"

    def test_apply_with_model_override(self) -> None:
        """Test applying config with model override."""
        base = ClaudeAgentOptions()
        result = apply_provider_config(
            base,
            "deepseek",
            model_override="deepseek-coder",
        )

        assert result.env is not None
        assert result.env["ANTHROPIC_MODEL"] == "deepseek-coder"

    def test_apply_bedrock(self) -> None:
        """Test applying bedrock provider config."""
        base = ClaudeAgentOptions()
        result = apply_provider_config(base, "bedrock")

        assert result.env is not None
        assert result.env["CLAUDE_CODE_USE_BEDROCK"] == "1"

    def test_apply_invalid_provider(self) -> None:
        """Test applying config for invalid provider raises error."""
        base = ClaudeAgentOptions()
        with pytest.raises(ValueError, match="Unknown provider"):
            apply_provider_config(base, "nonexistent")


class TestCreateOptionsForProvider:
    """Tests for create_options_for_provider function."""

    def test_create_for_anthropic(self) -> None:
        """Test creating options for anthropic provider."""
        options = create_options_for_provider(
            "anthropic",
            cwd="/test",
            max_turns=10,
        )

        assert options.cwd == "/test"
        assert options.max_turns == 10
        assert options.setting_sources == ["project"]

    def test_create_for_deepseek(self) -> None:
        """Test creating options for deepseek provider."""
        options = create_options_for_provider(
            "deepseek",
            api_key="sk-xxx",
            cwd="/test",
        )

        assert options.env is not None
        assert options.env["ANTHROPIC_BASE_URL"] == "https://api.deepseek.com/anthropic"
        assert options.env["ANTHROPIC_AUTH_TOKEN"] == "sk-xxx"

    def test_create_for_glm(self) -> None:
        """Test creating options for GLM provider."""
        options = create_options_for_provider(
            "glm",
            api_key="glm-key",
        )

        assert options.env is not None
        assert options.env["ANTHROPIC_BASE_URL"] == "https://api.z.ai/api/anthropic"
        assert options.env["ANTHROPIC_MODEL"] == "glm-4.5-air"

    def test_create_invalid_provider(self) -> None:
        """Test creating options for invalid provider raises error."""
        with pytest.raises(ValueError, match="Unknown provider"):
            create_options_for_provider("nonexistent")


class TestGetProviderEnvExample:
    """Tests for get_provider_env_example function."""

    def test_anthropic_example(self) -> None:
        """Test env example for anthropic."""
        example = get_provider_env_example("anthropic")
        assert "# Anthropic configuration" in example
        assert "ANTHROPIC_AUTH_TOKEN" in example

    def test_deepseek_example(self) -> None:
        """Test env example for deepseek."""
        example = get_provider_env_example("deepseek")
        assert "# DeepSeek configuration" in example
        assert "ANTHROPIC_BASE_URL" in example
        assert "api.deepseek.com" in example
        assert "deepseek-chat" in example

    def test_bedrock_example(self) -> None:
        """Test env example for bedrock."""
        example = get_provider_env_example("bedrock")
        assert "CLAUDE_CODE_USE_BEDROCK" in example

    def test_invalid_provider(self) -> None:
        """Test env example for invalid provider raises error."""
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider_env_example("nonexistent")


class TestGetCurrentProviderInfo:
    """Tests for get_current_provider_info function."""

    def test_default_is_anthropic(self) -> None:
        """Test default provider is anthropic when no env vars set."""
        # Clear relevant env vars
        env_backup = {}
        for key in ["ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX"]:
            env_backup[key] = os.environ.pop(key, None)

        try:
            info = get_current_provider_info()
            assert info["name"] == "anthropic"
            assert info["official"] is True
        finally:
            # Restore env vars
            for key, value in env_backup.items():
                if value is not None:
                    os.environ[key] = value

    def test_detects_deepseek_from_base_url(self) -> None:
        """Test detection of deepseek from base URL."""
        env_backup = {
            "ANTHROPIC_BASE_URL": os.environ.get("ANTHROPIC_BASE_URL"),
            "CLAUDE_CODE_USE_BEDROCK": os.environ.pop("CLAUDE_CODE_USE_BEDROCK", None),
            "CLAUDE_CODE_USE_VERTEX": os.environ.pop("CLAUDE_CODE_USE_VERTEX", None),
        }

        try:
            os.environ["ANTHROPIC_BASE_URL"] = "https://api.deepseek.com/anthropic"
            info = get_current_provider_info()
            assert info["name"] == "deepseek"
            assert info["official"] is False
        finally:
            if env_backup["ANTHROPIC_BASE_URL"]:
                os.environ["ANTHROPIC_BASE_URL"] = env_backup["ANTHROPIC_BASE_URL"]
            else:
                os.environ.pop("ANTHROPIC_BASE_URL", None)
            for key in ["CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX"]:
                if env_backup.get(key):
                    os.environ[key] = env_backup[key]

    def test_detects_bedrock(self) -> None:
        """Test detection of bedrock provider."""
        env_backup = os.environ.get("CLAUDE_CODE_USE_BEDROCK")

        try:
            os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
            info = get_current_provider_info()
            assert info["name"] == "bedrock"
            assert info["official"] is True
        finally:
            if env_backup:
                os.environ["CLAUDE_CODE_USE_BEDROCK"] = env_backup
            else:
                os.environ.pop("CLAUDE_CODE_USE_BEDROCK", None)
