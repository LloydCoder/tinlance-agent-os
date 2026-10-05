from tinlance_agent_os.handoff import Handoff,synthesize
def test_synthesis_preserves_evidence_refs():
 h=synthesize((Handoff("1","r","a","completed",("f",),("e1",),confidence=.8),Handoff("2","r","b","completed",("f2",),("e2",),confidence=.6)))
 assert h.evidence_refs==("e1","e2") and h.confidence==.7
