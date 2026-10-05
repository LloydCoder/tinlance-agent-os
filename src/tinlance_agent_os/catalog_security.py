"""Agentic threat-model invariants for Catalog/team planning."""
from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class SecurityScenario:
    scenario_id:str;category:str;fail_closed:bool;critical:bool=True
REQUIRED_SCENARIOS=(
 SecurityScenario("AGT-001","identity_spoofing",True),
 SecurityScenario("AGT-002","delegation_escalation",True),
 SecurityScenario("AGT-003","cross_tenant",True),
 SecurityScenario("AGT-004","message_replay",True),
 SecurityScenario("AGT-005","recursive_spawning",True),
 SecurityScenario("AGT-006","budget_storm",True),
 SecurityScenario("AGT-007","evidence_tampering",True),
 SecurityScenario("AGT-008","rogue_package",True),
 SecurityScenario("AGT-009","prompt_goal_hijack",True),
 SecurityScenario("AGT-010","cascading_failure",True),
)
def validate_security_suite()->None:
 if any(not s.fail_closed for s in REQUIRED_SCENARIOS): raise ValueError("critical security scenario must fail closed")
