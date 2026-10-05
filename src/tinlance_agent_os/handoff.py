"""Evidence-first inter-agent handoff and synthesis contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Handoff:
    task_id: str
    parent_task_id: str
    agent_id: str
    status: str
    findings: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    confidence: float = 0.0
    unresolved_questions: tuple[str, ...] = ()
    recommended_next_tasks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be 0..1")
        if not self.task_id or not self.agent_id:
            raise ValueError("task and agent are required")
        if not self.status:
            raise ValueError("handoff status is required")


def synthesize(handoffs: tuple[Handoff, ...]) -> Handoff:
    evidence = tuple(dict.fromkeys(item for handoff in handoffs for item in handoff.evidence_refs))
    findings = tuple(dict.fromkeys(item for handoff in handoffs for item in handoff.findings))
    confidence = (
        sum(handoff.confidence for handoff in handoffs) / len(handoffs) if handoffs else 0.0
    )
    return Handoff(
        "synthesis",
        "root",
        "reviewer",
        "completed",
        findings,
        evidence,
        (),
        confidence,
    )
