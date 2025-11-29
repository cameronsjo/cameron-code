"""Cameron Code - Extended Claude Code wrapper for testing SDK capabilities."""

from .client import CameronCodeClient
from .tools import cameron_search, cameron_time

__all__ = ["CameronCodeClient", "cameron_search", "cameron_time"]
