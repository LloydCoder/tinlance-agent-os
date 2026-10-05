from tinlance_agent_os.catalog_ga import CatalogGaReadiness, GaCheck


def checks(passed: bool = True) -> tuple[GaCheck, ...]:
    return tuple(
        GaCheck(name, passed, f"evidence:{name}")
        for name in (
            "ci",
            "architecture",
            "security",
            "evaluation",
            "supply_chain",
            "documentation",
        )
    )


def test_ga_readiness_requires_complete_evidence() -> None:
    readiness = CatalogGaReadiness(
        "2.0.0",
        "2",
        "2",
        420,
        0,
        checks(),
    )
    assert readiness.ready


def test_ga_readiness_fails_closed_on_failed_gate() -> None:
    readiness = CatalogGaReadiness(
        "2.0.0",
        "2",
        "2",
        420,
        0,
        checks(False),
    )
    assert not readiness.ready
