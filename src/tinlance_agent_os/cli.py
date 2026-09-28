"""Minimal CLI entry point for the Agent OS foundation."""

from . import __version__


def main() -> int:
    print(f"Tinlance Agentic OS {__version__}")
    return 0
