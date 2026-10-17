from tinlance_agent_os.catalog_candidates import canonical_semantic_key


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
