import pytest

from tinlance_agent_os.catalog_external import (
    ExternalDiscoverySource,
    ExternalSkill,
    normalize_a2a_agent_card,
)


def card() -> dict[str, object]:
    return {
        "name": "Threat Research Agent",
        "description": "Performs bounded threat research.",
        "version": "1.0.0",
        "supportedInterfaces": [
            {
                "url": "https://agents.example.test/a2a",
                "protocolBinding": "HTTP+JSON",
                "protocolVersion": "1.0",
            }
        ],
        "securitySchemes": {"oauth2": {}},
        "skills": [
            {
                "id": "threat-research",
                "name": "Threat Research",
                "description": "Researches threat intelligence.",
                "tags": ["threat", "research"],
            }
        ],
    }


def test_normalizes_a2a_v1_without_granting_authority() -> None:
    manifest = normalize_a2a_agent_card(card(), "a2a:https://agents.example.test/card")
    assert manifest.source is ExternalDiscoverySource.A2A_AGENT_CARD
    assert manifest.endpoint == "https://agents.example.test/a2a"
    assert manifest.security_schemes == ("oauth2",)
    assert manifest.signed is False


def test_a2a_v1_requires_supported_interfaces() -> None:
    invalid = card()
    invalid.pop("supportedInterfaces")
    with pytest.raises(ValueError, match="supportedInterfaces"):
        normalize_a2a_agent_card(invalid, "a2a:missing-interface")


def test_a2a_requires_https() -> None:
    invalid = card()
    invalid["supportedInterfaces"] = [
        {
            "url": "http://agents.example.test/a2a",
            "protocolBinding": "HTTP+JSON",
            "protocolVersion": "1.0",
        }
    ]
    with pytest.raises(ValueError, match="HTTPS"):
        normalize_a2a_agent_card(invalid, "a2a:insecure")


def test_external_skill_rejects_duplicate_tags() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ExternalSkill("x", "X", "X", tags=("a", "a"))


def test_a2a_requires_skills() -> None:
    invalid = card()
    invalid["skills"] = []
    with pytest.raises(ValueError, match="at least one skill"):
        normalize_a2a_agent_card(invalid, "a2a:no-skills")


def test_curated_catalog_record_maps_to_candidate_with_provenance() -> None:
    from tinlance_agent_os.catalog_external import normalize_curated_catalog_record

    record = normalize_curated_catalog_record(
        {
            "name": "Billing Agent",
            "description": "Analyzes billing records and identifies reconciliation exceptions.",
            "domain": "finance",
            "capabilities": ["billing.analysis", "billing.reconciliation"],
            "skills": ["exception-analysis"],
        },
        "vendor:catalog/42",
    )
    candidate = record.to_candidate()
    assert candidate.source_refs == ("curated-catalog:vendor:catalog/42",)
    assert candidate.capabilities == ("billing.analysis", "billing.reconciliation")


def test_curated_catalog_bounds_untrusted_input() -> None:
    from tinlance_agent_os.catalog_external import normalize_curated_catalog_record

    base = {
        "name": "Billing Agent",
        "description": "Analyzes billing records and identifies reconciliation exceptions.",
        "domain": "finance",
        "capabilities": ["billing.analysis"],
    }
    oversized = dict(base, name="x" * 4097)
    with pytest.raises(ValueError, match="maximum length"):
        normalize_curated_catalog_record(oversized, "vendor:42")

    too_many = dict(base, capabilities=["x"] * 257)
    with pytest.raises(ValueError, match="maximum item count"):
        normalize_curated_catalog_record(too_many, "vendor:42")


def test_curated_catalog_requires_capabilities() -> None:
    from tinlance_agent_os.catalog_external import normalize_curated_catalog_record

    with pytest.raises(ValueError, match="capabilities"):
        normalize_curated_catalog_record(
            {
                "name": "Billing Agent",
                "description": "Analyzes billing records and identifies reconciliation exceptions.",
                "domain": "finance",
                "capabilities": [],
            },
            "vendor:42",
        )
