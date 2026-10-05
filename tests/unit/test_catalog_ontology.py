from tinlance_agent_os.catalog_ontology import (
    Archetype,
    Capability,
    CapabilityFamily,
    Domain,
    OntologyId,
    OntologyKind,
    Role,
    Skill,
    implements,
    requires,
)


def oid(kind: OntologyKind, value: str) -> OntologyId:
    return OntologyId(kind, value)


def test_canonical_ontology_hierarchy() -> None:
    domain = Domain(oid(OntologyKind.DOMAIN, "security"), "Security", "Security work")
    family = CapabilityFamily(
        oid(OntologyKind.CAPABILITY_FAMILY, "security.application"),
        domain.id,
        "Application Security",
        "Application security capabilities",
    )
    capability = Capability(
        oid(OntologyKind.CAPABILITY, "security.application.review"),
        family.id,
        "Application Security Review",
        "Review application security posture",
    )
    skill = Skill(
        oid(OntologyKind.SKILL, "security.application.static_review"),
        capability.id,
        "Static Review",
        "Review static artifacts",
    )
    assert skill.capability_id == capability.id
    assert capability.family_id == family.id
    assert family.domain_id == domain.id


def test_roles_and_archetypes_are_non_authoritative_semantic_nodes() -> None:
    role = Role(oid(OntologyKind.ROLE, "reviewer"), "Reviewer", "Reviews work")
    archetype = Archetype(
        oid(OntologyKind.ARCHETYPE, "specialist"),
        "Specialist",
        "Focused specialist behavior",
    )
    assert role.id.kind is OntologyKind.ROLE
    assert archetype.id.kind is OntologyKind.ARCHETYPE


def test_relationships_are_descriptive() -> None:
    agent = oid(OntologyKind.ARCHETYPE, "security.specialist")
    capability = oid(OntologyKind.CAPABILITY, "security.application.review")
    relation = implements(agent, capability)
    assert relation.predicate == "implements"
    dependency = requires(capability, oid(OntologyKind.CAPABILITY, "security.source_analysis"))
    assert dependency.predicate == "requires_capability"


def test_ontology_rejects_cross_layer_parent_types() -> None:
    domain = oid(OntologyKind.DOMAIN, "security")
    try:
        CapabilityFamily(
            oid(OntologyKind.CAPABILITY_FAMILY, "security.app"),
            oid(OntologyKind.CAPABILITY, "wrong"),
            "App",
            "Invalid",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("cross-layer ontology reference must fail")
    assert domain.kind is OntologyKind.DOMAIN
