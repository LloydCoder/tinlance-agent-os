from tinlance_agent_os.handoff import Handoff, synthesize


def test_synthesis_preserves_evidence_refs() -> None:
    result = synthesize(
        (
            Handoff(
                "1",
                "r",
                "a",
                "completed",
                ("f",),
                ("e1",),
                confidence=0.8,
            ),
            Handoff(
                "2",
                "r",
                "b",
                "completed",
                ("f2",),
                ("e2",),
                confidence=0.6,
            ),
        )
    )
    assert result.evidence_refs == ("e1", "e2")
    assert result.confidence == 0.7
