"""Untrusted external agent metadata normalization for Catalog v3.

External metadata is discovery evidence only. It never grants authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast
from urllib.parse import urlparse

from .catalog_candidates import TaxonomyCandidate


class ExternalDiscoverySource(StrEnum):
    A2A_AGENT_CARD = "a2a-agent-card"
    CURATED_CATALOG = "curated-catalog"
    DIRECT_CONFIG = "direct-config"


@dataclass(frozen=True, slots=True)
class ExternalSkill:
    id: str
    name: str
    description: str
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip() or not self.description.strip():
            raise ValueError("external skill identity and description are required")
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("duplicate external skill tags are not permitted")


@dataclass(frozen=True, slots=True)
class ExternalAgentManifest:
    source: ExternalDiscoverySource
    source_ref: str
    name: str
    description: str
    version: str
    endpoint: str
    skills: tuple[ExternalSkill, ...]
    security_schemes: tuple[str, ...] = ()
    signed: bool = False

    def __post_init__(self) -> None:
        if not self.source_ref.strip() or not self.name.strip():
            raise ValueError("external discovery identity is required")
        if not self.description.strip() or not self.version.strip():
            raise ValueError("external discovery metadata is incomplete")
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("external endpoint must be an absolute HTTP(S) URL")
        if not self.skills:
            raise ValueError("external manifests require at least one skill")
        if self.source is ExternalDiscoverySource.A2A_AGENT_CARD and parsed.scheme != "https":
            raise ValueError("A2A production discovery requires HTTPS")


def _a2a_endpoint(card: dict[str, object]) -> str:
    """Return the preferred A2A v1 interface URL; never trust legacy endpoint fields."""
    interfaces = card.get("supportedInterfaces")
    if not isinstance(interfaces, list) or not interfaces:
        raise ValueError("A2A Agent Card requires supportedInterfaces")
    first = interfaces[0]
    if not isinstance(first, dict):
        raise ValueError("A2A supported interface must be an object")
    endpoint = first.get("url")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError("A2A supported interface requires a URL")
    return endpoint


def normalize_a2a_agent_card(
    card: dict[str, object],
    source_ref: str,
) -> ExternalAgentManifest:
    """Normalize an A2A 1.0 Agent Card without trusting its declarations."""

    required = ("name", "description", "version")
    if any(not isinstance(card.get(key), str) or not str(card[key]).strip() for key in required):
        raise ValueError("A2A Agent Card is missing required discovery fields")

    raw_skills = card["skills"]
    if not isinstance(raw_skills, list):
        raise ValueError("A2A skills must be an array")

    skills: list[ExternalSkill] = []
    for raw in raw_skills:
        if not isinstance(raw, dict):
            raise ValueError("A2A skill must be an object")
        tags = raw.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("A2A skill tags must be strings")
        skills.append(
            ExternalSkill(
                id=str(raw.get("id", "")),
                name=str(raw.get("name", "")),
                description=str(raw.get("description", "")),
                tags=tuple(tags),
            )
        )

    schemes = card.get("securitySchemes", {})
    security_schemes = tuple(schemes.keys()) if isinstance(schemes, dict) else ()

    return ExternalAgentManifest(
        source=ExternalDiscoverySource.A2A_AGENT_CARD,
        source_ref=source_ref,
        name=str(card["name"]),
        description=str(card["description"]),
        version=str(card["version"]),
        endpoint=_a2a_endpoint(card),
        skills=tuple(skills),
        security_schemes=security_schemes,
        signed=bool(card.get("signatures")),
    )


@dataclass(frozen=True, slots=True)
class ExternalCatalogRecord:
    """Generic descriptive record from an external catalog."""

    source_ref: str
    name: str
    description: str
    domain: str
    capabilities: tuple[str, ...]
    skills: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_ref.strip() or not self.name.strip():
            raise ValueError("external catalog identity is required")
        if not self.description.strip() or not self.domain.strip():
            raise ValueError("external catalog metadata is incomplete")
        if not self.capabilities:
            raise ValueError("external catalog records require capabilities")

    def to_candidate(self) -> TaxonomyCandidate:
        return TaxonomyCandidate(
            name=self.name,
            description=self.description,
            domain=self.domain,
            capabilities=self.capabilities,
            skills=self.skills,
            source_refs=(f"{ExternalDiscoverySource.CURATED_CATALOG.value}:{self.source_ref}",),
        )


def _bounded_text(value: Any, field: str, *, max_length: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{field} exceeds maximum length")
    return str(value)


def _bounded_strings(value: Any, field: str, *, max_items: int = 256) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    if len(value) > max_items:
        raise ValueError(f"{field} exceeds maximum item count")
    result = tuple(
        _bounded_text(item, f"{field}[{index}]", max_length=512) for index, item in enumerate(value)
    )
    return result


def normalize_curated_catalog_record(
    record: dict[str, Any], source_ref: str
) -> ExternalCatalogRecord:
    """Normalize a bounded generic catalog record into untrusted descriptive metadata."""
    if not isinstance(record, dict):
        raise ValueError("external catalog record must be an object")
    capabilities = _bounded_strings(record.get("capabilities"), "capabilities")
    skills_value = record.get("skills", [])
    skills = _bounded_strings(skills_value, "skills") if skills_value else ()
    return ExternalCatalogRecord(
        source_ref=_bounded_text(source_ref, "source_ref", max_length=2048),
        name=_bounded_text(record.get("name"), "name"),
        description=_bounded_text(record.get("description"), "description"),
        domain=_bounded_text(record.get("domain"), "domain", max_length=512),
        capabilities=capabilities,
        skills=skills,
    )
