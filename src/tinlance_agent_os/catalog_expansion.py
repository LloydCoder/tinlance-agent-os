"""Controlled 2K-scale Agent Catalog v3 archetype expansion.

Phase 26 combines canonical semantic domains with a bounded, domain-neutral
work-pattern vocabulary. The Cartesian product is intentional: each emitted
archetype represents a distinct domain + work boundary, while provider,
model, geography, deployment, tool, protocol, cost, latency, and authority
remain outside taxonomy identity.
"""

from __future__ import annotations

from .catalog_domains import build_domain_catalog
from .catalog_taxonomy import CanonicalAgentArchetype, TaxonomyProvenance, TaxonomyStatus

_WORK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("analyze", "analyzes information to identify relevant structure or meaning"),
    ("classify", "classifies information into defined semantic categories"),
    ("compare", "compares alternatives, records, or states against explicit criteria"),
    ("correlate", "correlates related observations to identify meaningful relationships"),
    ("detect", "detects the presence of defined conditions or anomalies"),
    ("discover", "discovers previously unidentified information or relationships"),
    ("extract", "extracts structured information from source material"),
    ("retrieve", "retrieves relevant information from an available knowledge source"),
    ("search", "searches defined information spaces for relevant evidence"),
    ("summarize", "summarizes source information into a bounded coherent representation"),
    ("synthesize", "synthesizes multiple inputs into a coherent result"),
    ("interpret", "interprets information according to the declared domain context"),
    ("explain", "explains domain information, relationships, or outcomes"),
    ("translate", "translates information between supported representations or languages"),
    ("transform", "transforms information into a declared target representation"),
    ("generate", "generates a domain-relevant artifact from declared inputs"),
    ("draft", "drafts a domain-relevant artifact for review or downstream use"),
    ("review", "reviews an artifact or state against declared criteria"),
    ("audit", "audits evidence or artifacts against defined control criteria"),
    ("verify", "verifies a claim, artifact, or state against available evidence"),
    ("validate", "validates conformance to explicit semantic or quality criteria"),
    ("benchmark", "benchmarks a result or system against defined measures"),
    ("measure", "measures a defined property, outcome, or state"),
    ("monitor", "monitors a defined process, quality, or state over time"),
    ("forecast", "forecasts likely future states from available evidence"),
    ("estimate", "estimates a quantity or outcome using declared assumptions"),
    ("predict", "predicts a likely outcome from available evidence"),
    ("model", "models a domain process, relationship, or scenario"),
    ("simulate", "simulates a defined scenario to examine possible outcomes"),
    ("plan", "develops a bounded plan for achieving a declared outcome"),
    ("prioritize", "prioritizes alternatives using declared criteria"),
    ("recommend", "recommends viable options without granting execution authority"),
    ("optimize", "identifies improvements against defined objectives and constraints"),
    ("reconcile", "reconciles differences between records, states, or representations"),
    ("map", "maps relationships between domain entities, concepts, or states"),
    ("trace", "traces provenance, lineage, dependencies, or state transitions"),
    ("report", "produces a structured report from declared inputs and evidence"),
    ("document", "documents domain state, decisions, procedures, or findings"),
    ("investigate", "investigates a bounded question using available evidence"),
    ("triage", "triages items into defined handling categories without exercising authority"),
    ("schedule", "proposes or organizes timing for declared activities"),
    ("route", "routes items according to declared semantic criteria"),
    ("coordinate", "coordinates information or work dependencies without replacing M17 execution"),
)

def _slug(value: str) -> str:
    return value.casefold().replace("_", "-").replace(" ", "-")

def build_phase_26_catalog() -> tuple[CanonicalAgentArchetype, ...]:
    """Build the deterministic 48 × 42 = 2,016 archetype expansion."""
    result: list[CanonicalAgentArchetype] = []
    for domain in build_domain_catalog():
        for pattern_id, pattern_description in _WORK_PATTERNS:
            result.append(
                CanonicalAgentArchetype(
                    id=f"{domain.id}.{_slug(pattern_id)}.agent",
                    version="1.0.0",
                    name=f"{domain.name} {pattern_id.replace('-', ' ').title()} Agent",
                    description=(
                        f"{pattern_description.capitalize()} within the "
                        f"{domain.name.lower()} domain."
                    ),
                    domain_id=domain.id,
                    capability_ids=(f"work.{_slug(pattern_id)}",),
                    skill_ids=(f"work.{_slug(pattern_id)}",),
                    inclusion_criteria=(
                        f"work materially belongs to {domain.id}",
                        f"work performs the {pattern_id} semantic activity",
                    ),
                    exclusion_criteria=(
                        "does not encode geography, customer, provider, model, "
                        "tool, protocol, deployment, cost, latency, or authorization",
                    ),
                    provenance=(
                        TaxonomyProvenance(
                            source_id="agent-catalog-v3-phase-26",
                            source_type="controlled-expansion",
                            reference=f"{domain.id}:{pattern_id}",
                            method="domain-work-pattern Cartesian product",
                        ),
                    ),
                    status=TaxonomyStatus.CANONICAL,
                )
            )
    return tuple(result)

def phase_26_count() -> int:
    return len(build_domain_catalog()) * len(_WORK_PATTERNS)
