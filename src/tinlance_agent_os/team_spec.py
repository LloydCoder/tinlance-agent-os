"""Bounded dynamic-team contract."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
class TeamTopology(StrEnum): SINGLE="single";SEQUENTIAL="sequential";PARALLEL="parallel";HIERARCHICAL="hierarchical";DAG="dag";REVIEW_LOOP="review_loop";HUMAN_ESCALATION="human_escalation"
@dataclass(frozen=True,slots=True)
class TeamBudget:
    max_agents:int=1;max_active_agents:int=1;max_depth:int=0;max_fanout:int=0;max_runtime_seconds:int=300;max_tokens:int=100000;max_tool_calls:int=100;max_cost_microunits:int=0;max_retries:int=2
    def __post_init__(self)->None:
        if min(self.max_agents,self.max_active_agents,self.max_depth,self.max_fanout,self.max_runtime_seconds,self.max_tokens,self.max_tool_calls,self.max_cost_microunits,self.max_retries)<0: raise ValueError("team limits cannot be negative")
@dataclass(frozen=True,slots=True)
class TeamSpec:
    team_id:str;goal:str;workspace_id:str;supervisor:str;members:tuple[str,...];topology:TeamTopology;budget:TeamBudget;approval_policy:str="platform-default";evidence_policy:str="required";failure_policy:str="fail_closed";synthesis_policy:str="evidence_first"
    def __post_init__(self)->None:
        if not self.team_id or not self.goal or not self.workspace_id or not self.supervisor: raise ValueError("team identity and goal are required")
        if len(self.members)>self.budget.max_agents: raise ValueError("team exceeds max_agents")
