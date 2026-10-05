"""Evidence-first inter-agent handoff and synthesis contract."""
from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class Handoff:
    task_id:str;parent_task_id:str;agent_id:str;status:str;findings:tuple[str,...]=();evidence_refs:tuple[str,...]=();artifacts:tuple[str,...]=();confidence:float=0.0;unresolved_questions:tuple[str,...]=();recommended_next_tasks:tuple[str,...]=()
    def __post_init__(self)->None:
        if not 0.0<=self.confidence<=1.0: raise ValueError("confidence must be 0..1")
        if not self.task_id or not self.agent_id: raise ValueError("task and agent are required")
def synthesize(handoffs:tuple[Handoff,...])->Handoff:
    evidence=tuple(dict.fromkeys(x for h in handoffs for x in h.evidence_refs))
    findings=tuple(dict.fromkeys(x for h in handoffs for x in h.findings))
    return Handoff("synthesis","root","reviewer","completed",findings,evidence,(),sum(h.confidence for h in handoffs)/len(handoffs) if handoffs else 0.0)
