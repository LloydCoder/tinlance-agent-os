"""Protocol-neutral external agent/tool metadata adapters.

This module only validates and describes remote protocol metadata. It does not
create credentials, authorize tools, or confer execution authority.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


def _required_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a normalized non-empty string")
    return value


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a sequence")
    if not all(isinstance(item, str) and item and item == item.strip() for item in value):
        raise ValueError(f"{name} entries must be normalized non-empty strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{name} entries must be unique")
    return tuple(value)


def _endpoint(value: object) -> str:
    endpoint = _required_string(value, "protocol endpoint")
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.netloc:
        raise ValueError("remote protocol endpoint must use HTTPS")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise ValueError("remote protocol endpoint must not embed credentials or fragments")
    if parsed.query:
        raise ValueError("remote protocol endpoint must not contain query parameters")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("remote protocol endpoint port is invalid") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("remote protocol endpoint port is invalid")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("remote protocol endpoint must not target localhost")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("remote protocol endpoint must not target a non-public IP address")
    return endpoint


@dataclass(frozen=True, slots=True)
class ProtocolProfile:
    protocol: str
    version: str
    endpoint: str
    capabilities: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    security_schemes: tuple[str, ...] = ()
    provenance: str = ""

    def __post_init__(self) -> None:
        if self.protocol not in {"mcp", "a2a"}:
            raise ValueError("unsupported external protocol")
        _required_string(self.version, "protocol version")
        _endpoint(self.endpoint)
        _string_tuple(self.capabilities, "capabilities")
        _string_tuple(self.skills, "skills")
        _string_tuple(self.security_schemes, "security schemes")
        if self.provenance and self.provenance != self.provenance.strip():
            raise ValueError("provenance must be normalized when supplied")


def _capability_names(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return _string_tuple(value, "capabilities")
    if isinstance(value, dict):
        names = tuple(
            key for key, enabled in value.items()
            if isinstance(key, str) and enabled is True
        )
        if any(not isinstance(key, str) for key in value):
            raise ValueError("capability names must be strings")
        return tuple(sorted(names))
    raise ValueError("capabilities must be a list or object")


def _names_from_records(value: object, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a sequence")
    names: list[str] = []
    for record in value:
        if isinstance(record, str):
            item = _required_string(record, name)
        elif isinstance(record, dict):
            candidate = record.get("id", record.get("name"))
            item = _required_string(candidate, f"{name} identifier")
        else:
            raise ValueError(f"{name} entries must be strings or objects")
        if item in names:
            raise ValueError(f"{name} identifiers must be unique")
        names.append(item)
    return tuple(names)


def from_a2a_card(card: dict[str, object]) -> ProtocolProfile:
    if not isinstance(card, dict):
        raise ValueError("A2A Agent Card must be an object")
    interfaces = card.get("supportedInterfaces")
    if interfaces is not None:
        if (
            not isinstance(interfaces, list)
            or not interfaces
            or not isinstance(interfaces[0], dict)
        ):
            raise ValueError("A2A supportedInterfaces must contain an interface object")
        endpoint = interfaces[0].get("url")
        version = interfaces[0].get("protocolVersion", card.get("protocolVersion", "1.0"))
    else:
        endpoint = card.get("url", card.get("endpoint"))
        version = card.get("protocolVersion", card.get("version", "unknown"))
    schemes = card.get("securitySchemes", card.get("security_schemes", ()))
    if isinstance(schemes, dict):
        scheme_names = tuple(sorted(schemes))
    else:
        scheme_names = _string_tuple(schemes, "A2A security schemes")
    provider = card.get("provider", "")
    if isinstance(provider, dict):
        provider = provider.get("organization", provider.get("name", ""))
    if not isinstance(provider, str):
        raise ValueError("A2A provider provenance must be a string or provider object")
    return ProtocolProfile(
        "a2a",
        _required_string(version, "A2A protocol version"),
        _endpoint(endpoint),
        _capability_names(card.get("capabilities")),
        _names_from_records(card.get("skills"), "A2A skills"),
        scheme_names,
        provider,
    )


def from_mcp_metadata(meta: dict[str, object]) -> ProtocolProfile:
    if not isinstance(meta, dict):
        raise ValueError("MCP metadata must be an object")
    server_info = meta.get("serverInfo", meta.get("server_info", {}))
    if server_info is not None and not isinstance(server_info, dict):
        raise ValueError("MCP serverInfo must be an object")
    transport = meta.get("transport", {})
    if transport is not None and not isinstance(transport, dict):
        raise ValueError("MCP transport metadata must be an object")
    endpoint = meta.get("endpoint")
    if endpoint is None and isinstance(transport, dict):
        endpoint = transport.get("endpoint")
    version = meta.get("protocolVersion", meta.get("protocol_version"))
    if version is None and isinstance(server_info, dict):
        version = server_info.get("version")
    tools = _names_from_records(meta.get("tools"), "MCP tools")
    capabilities = _capability_names(meta.get("capabilities"))
    schemes = meta.get("securitySchemes", meta.get("security_schemes", ()))
    if isinstance(schemes, dict):
        scheme_names = tuple(sorted(schemes))
    else:
        scheme_names = _string_tuple(schemes, "MCP security schemes")
    server = meta.get("server", "")
    if isinstance(server, dict):
        server = server.get("name", "")
    if not isinstance(server, str):
        raise ValueError("MCP server provenance must be a string or server object")
    return ProtocolProfile(
        "mcp",
        _required_string(version, "MCP protocol version"),
        _endpoint(endpoint),
        tuple(sorted(set(capabilities) | set(tools))),
        (),
        scheme_names,
        server,
    )
