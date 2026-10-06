"""Controlled domain expansion for Agent Catalog v3.

Domains describe semantic work areas. They are not industries-as-geography,
deployment targets, permissions, models, tools, or customer identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DomainFamily(StrEnum):
    ENGINEERING = "engineering"
    SECURITY = "security"
    DATA = "data"
    BUSINESS = "business"
    REGULATED = "regulated"
    SCIENCE = "science"
    HUMAN_SERVICES = "human-services"
    OPERATIONS = "operations"


@dataclass(frozen=True, slots=True)
class CanonicalDomain:
    id: str
    family: DomainFamily
    name: str
    description: str
    inclusion_criteria: tuple[str, ...]
    exclusion_criteria: tuple[str, ...]
    version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not self.id or self.id != self.id.strip() or "." not in self.id:
            raise ValueError("domain id must be namespaced")
        if not self.version.strip() or not self.name.strip() or not self.description.strip():
            raise ValueError("domain identity and description are required")
        if not self.inclusion_criteria or not self.exclusion_criteria:
            raise ValueError("domain inclusion and exclusion criteria are required")

    @property
    def semantic_key(self) -> str:
        return f"{self.id}|{self.name.casefold().strip()}"

    def to_record(self) -> dict[str, object]:
        return {
            "schema": "tinlance.agent-domain.v1",
            "id": self.id,
            "family": self.family.value,
            "name": self.name,
            "description": self.description,
            "inclusion_criteria": list(self.inclusion_criteria),
            "exclusion_criteria": list(self.exclusion_criteria),
            "version": self.version,
        }


_DOMAIN_SEEDS: tuple[tuple[str, DomainFamily, str], ...] = (
    (
        "engineering.software",
        DomainFamily.ENGINEERING,
        "Software engineering and application development",
    ),
    (
        "engineering.platform",
        DomainFamily.ENGINEERING,
        "Platform engineering and developer infrastructure",
    ),
    (
        "engineering.reliability",
        DomainFamily.ENGINEERING,
        "Reliability engineering and service resilience",
    ),
    (
        "engineering.quality",
        DomainFamily.ENGINEERING,
        "Software quality, testing and verification",
    ),
    (
        "engineering.ai",
        DomainFamily.ENGINEERING,
        "AI engineering, model integration and agent systems",
    ),
    (
        "engineering.hardware",
        DomainFamily.ENGINEERING,
        "Hardware engineering and embedded systems",
    ),
    (
        "security.cybersecurity",
        DomainFamily.SECURITY,
        "Cybersecurity defense, assessment and response",
    ),
    (
        "security.identity",
        DomainFamily.SECURITY,
        "Digital identity, authentication and access management",
    ),
    (
        "security.privacy",
        DomainFamily.SECURITY,
        "Privacy engineering and data protection",
    ),
    (
        "security.trust",
        DomainFamily.SECURITY,
        "Trust, assurance and security governance",
    ),
    (
        "data.engineering",
        DomainFamily.DATA,
        "Data pipelines, platforms and lifecycle engineering",
    ),
    (
        "data.analytics",
        DomainFamily.DATA,
        "Analytics, business intelligence and quantitative analysis",
    ),
    (
        "data.science",
        DomainFamily.DATA,
        "Statistical learning, machine learning and data science",
    ),
    (
        "data.knowledge",
        DomainFamily.DATA,
        "Knowledge management, retrieval and information synthesis",
    ),
    (
        "data.observability",
        DomainFamily.DATA,
        "Data quality, lineage, observability and monitoring",
    ),
    (
        "business.finance",
        DomainFamily.BUSINESS,
        "Finance, accounting, treasury and financial operations",
    ),
    (
        "business.revenue",
        DomainFamily.BUSINESS,
        "Revenue operations, sales and commercial execution",
    ),
    (
        "business.marketing",
        DomainFamily.BUSINESS,
        "Marketing, growth and market intelligence",
    ),
    (
        "business.customer",
        DomainFamily.BUSINESS,
        "Customer success, support and service operations",
    ),
    (
        "business.strategy",
        DomainFamily.BUSINESS,
        "Corporate strategy, planning and decision support",
    ),
    (
        "business.procurement",
        DomainFamily.BUSINESS,
        "Procurement, sourcing and supplier management",
    ),
    (
        "business.people",
        DomainFamily.BUSINESS,
        "Human resources, talent and people operations",
    ),
    (
        "business.legal",
        DomainFamily.BUSINESS,
        "Legal operations, contracts and legal information",
    ),
    (
        "regulated.healthcare",
        DomainFamily.REGULATED,
        "Healthcare operations, clinical administration and health information",
    ),
    (
        "regulated.fintech",
        DomainFamily.REGULATED,
        "Financial technology operations and regulated financial workflows",
    ),
    (
        "regulated.insurance",
        DomainFamily.REGULATED,
        "Insurance underwriting, claims and policy operations",
    ),
    (
        "regulated.pharma",
        DomainFamily.REGULATED,
        "Pharmaceutical and life-science regulated operations",
    ),
    (
        "regulated.public-sector",
        DomainFamily.REGULATED,
        "Public-sector administration and civic service workflows",
    ),
    (
        "science.life",
        DomainFamily.SCIENCE,
        "Biology, life science and biomedical research",
    ),
    (
        "science.physical",
        DomainFamily.SCIENCE,
        "Physics, chemistry and physical science",
    ),
    (
        "science.earth",
        DomainFamily.SCIENCE,
        "Earth, environmental and climate science",
    ),
    (
        "science.space",
        DomainFamily.SCIENCE,
        "Astronomy, space science and mission analysis",
    ),
    (
        "science.social",
        DomainFamily.SCIENCE,
        "Social science, behavioral and demographic research",
    ),
    (
        "science.quantitative",
        DomainFamily.SCIENCE,
        "Mathematics, statistics and quantitative methods",
    ),
    (
        "human.research",
        DomainFamily.HUMAN_SERVICES,
        "Research, investigation and evidence synthesis",
    ),
    (
        "human.communication",
        DomainFamily.HUMAN_SERVICES,
        "Communication, writing, translation and media workflows",
    ),
    (
        "human.design",
        DomainFamily.HUMAN_SERVICES,
        "Design, creative production and content development",
    ),
    (
        "human.education",
        DomainFamily.HUMAN_SERVICES,
        "Teaching, tutoring and educational content",
    ),
    (
        "human.accessibility",
        DomainFamily.HUMAN_SERVICES,
        "Accessibility, inclusion and assistive workflows",
    ),
    (
        "human.care",
        DomainFamily.HUMAN_SERVICES,
        "Care coordination and non-diagnostic human support",
    ),
    (
        "operations.supply-chain",
        DomainFamily.OPERATIONS,
        "Supply chain, logistics and inventory operations",
    ),
    (
        "operations.manufacturing",
        DomainFamily.OPERATIONS,
        "Manufacturing, production and industrial operations",
    ),
    (
        "operations.facilities",
        DomainFamily.OPERATIONS,
        "Facilities, property and workplace operations",
    ),
    (
        "operations.field-service",
        DomainFamily.OPERATIONS,
        "Field service, maintenance and dispatch operations",
    ),
    (
        "operations.program",
        DomainFamily.OPERATIONS,
        "Program, project and portfolio operations",
    ),
    (
        "operations.compliance",
        DomainFamily.OPERATIONS,
        "Compliance operations, controls and audit preparation",
    ),
    (
        "operations.intelligence",
        DomainFamily.OPERATIONS,
        "Operational intelligence, monitoring and situational awareness",
    ),
)


def build_domain_catalog() -> tuple[CanonicalDomain, ...]:
    """Build the phase seed without permitting duplicate canonical IDs."""
    seen: set[str] = set()
    result: list[CanonicalDomain] = []
    for identifier, family, description in _DOMAIN_SEEDS:
        if identifier in seen:
            raise ValueError(f"duplicate canonical domain id: {identifier}")
        seen.add(identifier)
        result.append(
            CanonicalDomain(
                id=identifier,
                family=family,
                name=identifier.rsplit(".", 1)[-1].replace("-", " ").title(),
                description=description,
                inclusion_criteria=(f"work semantically belongs to {identifier}",),
                exclusion_criteria=(
                    "does not encode geography, customer identity, model, tool, "
                    "protocol, or authorization",
                ),
            )
        )
    return tuple(result)
