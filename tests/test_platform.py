from tinlance_agent_os.domain import CorrelationId, RunId
from tinlance_agent_os.platform import PlatformEvidenceRef, PlatformRun


def test_platform_run_is_only_a_reference_to_governed_execution() -> None:
    run = PlatformRun(RunId("run-1"), CorrelationId("corr-1"), "running")
    assert run.run_id == RunId("run-1")


def test_platform_evidence_is_referenced_not_reimplemented() -> None:
    evidence = PlatformEvidenceRef("e-1", RunId("run-1"), "platform://evidence/e-1")
    assert evidence.uri == "platform://evidence/e-1"
