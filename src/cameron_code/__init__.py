"""Cameron Code - Extended Claude Code wrapper for testing SDK capabilities."""

from .client import CameronCodeClient
from .tools import cameron_search, cameron_time
from .providers import (
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

__all__ = [
    "CameronCodeClient",
    "cameron_search",
    "cameron_time",
    "ProviderConfig",
    "PROVIDERS",
    "get_provider",
    "list_providers",
    "create_custom_provider",
    "apply_provider_config",
    "create_options_for_provider",
    "get_provider_env_example",
    "get_current_provider_info",
]
