"""Cameron Code - Extended Claude Code wrapper for testing SDK capabilities."""

from .client import CameronCodeClient
from .tools import cameron_search, cameron_time
from .providers import (
    ProviderConfig,
    PROVIDERS,
    get_provider,
    list_providers,
    apply_provider_config,
    create_options_for_provider,
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
    "apply_provider_config",
    "create_options_for_provider",
    "get_current_provider_info",
]
