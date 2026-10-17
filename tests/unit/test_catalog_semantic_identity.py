from tinlance_agent_os.catalog_candidates import (
    CandidateState,
    TaxonomyCandidate,
    canonical_semantic_key,
    deduplicate,
)


def test_semantic_key_normalizes_case_whitespace_and_duplicate_tokens() -> None:
    first = canonical_semantic_key(
        "  Finance  ",
        ("Balance", " balance ", "ACCOUNTING"),
        (" Reconcile  Ledger ", "reconcile ledger"),
    )
    second = canonical_semantic_key(
        "finance",
        ("accounting", "BALANCE"),
        ("reconcile ledger",),
    )
    assert first == second


def test_semantic_key_uses_structured_encoding_to_prevent_delimiter_collisions() -> None:
    first = canonical_semantic_key("a|b", ("c",), ("skill",))
    second = canonical_semantic_key("a", ("b|c",), ("skill",))
    assert first != second


def test_candidate_deduplication_uses_canonical_identity_not_display_labels() -> None:
    first = TaxonomyCandidate(
        name="Finance Analyst",
        description="Analyzes finance workflows and produces structured outputs.",
        domain="Finance",
        capabilities=("Reconcile Ledger",),
        skills=("Accounting",),
        source_refs=("source:1",),
    )
    renamed = TaxonomyCandidate(
        name="Ledger Specialist",
        description="A differently described agent with the same semantic archetype.",
        domain=" finance ",
        capabilities=("reconcile ledger",),
        skills=("accounting",),
        source_refs=("source:1",),
    )
    forward = deduplicate((first, renamed))
    reverse = deduplicate((renamed, first))
    assert len(forward) == len(reverse) == 1
    assert forward[0].semantic_key == reverse[0].semantic_key
    assert forward[0].name == reverse[0].name
    assert forward[0].state is CandidateState.NORMALIZED
