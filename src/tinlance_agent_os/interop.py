"""Protocol-neutral external agent/tool metadata adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ProtocolProfile:
    protocol: str
    version: str
    endpoint: str
    capabilities: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    security_schemes: tuple[str, ...] = ()
    provenance: str = ""


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("protocol metadata list must be a sequence")
    if not all(isinstance(item, str) and item for item in value):
        raise ValueError("protocol metadata entries must be non-empty strings")
    return tuple(value)


def from_a2a_card(card: dict[str, object]) -> ProtocolProfile:
    return ProtocolProfile(
        "a2a",
        str(card.get("version", "unknown")),
        str(card.get("url", "")),
        _string_tuple(card.get("capabilities")),
        _string_tuple(card.get("skills")),
        _string_tuple(card.get("securitySchemes")),
        str(card.get("provider", "")),
    )


def from_mcp_metadata(meta: dict[str, object]) -> ProtocolProfile:
    return ProtocolProfile(
        "mcp",
        str(meta.get("version", "unknown")),
        str(meta.get("endpoint", "")),
        _string_tuple(meta.get("tools")),
        (),
        _string_tuple(meta.get("securitySchemes")),
        str(meta.get("server", "")),
    )
