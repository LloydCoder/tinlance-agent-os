"""Authority-neutral A2A/MCP interoperability metadata mapping."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class InteropProtocol(StrEnum):
    A2A = "a2a"
    MCP = "mcp"


@dataclass(frozen=True, slots=True)
class InteropMapping:
    protocol: InteropProtocol
    protocol_version: str
    identity: str
    capabilities: tuple[str, ...]
    skills: tuple[str, ...]
    input_modes: tuple[str, ...]
    output_modes: tuple[str, ...]
    interfaces: tuple[str, ...]
    security_schemes: tuple[str, ...]
    signed: bool
    provider_type: str

    def __post_init__(self) -> None:
        if not self.protocol_version.strip() or not self.identity.strip():
            raise ValueError("interoperability identity and version are required")
        if any(not value.strip() for value in self.capabilities + self.skills):
            raise ValueError("interoperability capabilities and skills must be non-empty")
        if any(not value.strip() for value in self.interfaces):
            raise ValueError("interoperability interfaces must be non-empty")
        for interface in self.interfaces:
            parsed = urlparse(interface)
            if parsed.scheme not in {"https", "grpc"}:
                raise ValueError("production interoperability interfaces must be HTTPS or gRPC")
        if self.protocol is InteropProtocol.A2A and not self.skills:
            raise ValueError("A2A mappings require at least one descriptive skill")
        if self.protocol is InteropProtocol.MCP and self.provider_type != "tool-provider":
            raise ValueError("MCP mappings must remain classified as tool-provider metadata")

    @property
    def fingerprint(self) -> str:
        payload = {
            "protocol": self.protocol.value,
            "protocol_version": self.protocol_version,
            "identity": self.identity,
            "capabilities": sorted(self.capabilities),
            "skills": sorted(self.skills),
            "input_modes": sorted(self.input_modes),
            "output_modes": sorted(self.output_modes),
            "interfaces": sorted(self.interfaces),
            "security_schemes": sorted(self.security_schemes),
            "signed": self.signed,
            "provider_type": self.provider_type,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def map_a2a_agent_card(
    *,
    name: str,
    version: str,
    capabilities: tuple[str, ...],
    skills: tuple[str, ...],
    interfaces: tuple[str, ...],
    input_modes: tuple[str, ...] = (),
    output_modes: tuple[str, ...] = (),
    security_schemes: tuple[str, ...] = (),
    signed: bool = False,
) -> InteropMapping:
    """Map A2A discovery metadata without granting authority."""
    return InteropMapping(
        protocol=InteropProtocol.A2A,
        protocol_version=version,
        identity=name,
        capabilities=capabilities,
        skills=skills,
        input_modes=input_modes,
        output_modes=output_modes,
        interfaces=interfaces,
        security_schemes=security_schemes,
        signed=signed,
        provider_type="agent",
    )


def map_mcp_server(
    *,
    name: str,
    version: str,
    tools: tuple[str, ...],
    resources: tuple[str, ...],
    prompts: tuple[str, ...],
    interface: str,
    signed: bool = False,
) -> InteropMapping:
    """Map MCP server primitives as tool-provider metadata, never as agents."""
    capabilities = tuple(sorted({f"tool:{value}" for value in tools} | {f"resource:{value}" for value in resources}))
    skills = tuple(sorted(f"prompt:{value}" for value in prompts))
    return InteropMapping(
        protocol=InteropProtocol.MCP,
        protocol_version=version,
        identity=name,
        capabilities=capabilities or ("mcp:provider",),
        skills=skills or ("mcp:provider",),
        input_modes=(),
        output_modes=(),
        interfaces=(interface,),
        security_schemes=(),
        signed=signed,
        provider_type="tool-provider",
    )
