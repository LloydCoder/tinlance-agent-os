"""Authority-neutral delegation proposal; Platform remains admission authority."""
from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class DelegationEnvelope:
    parent_agent:str;child_agent:str;tenant_id:str;workspace_id:str;capabilities:tuple[str,...];max_depth:int;max_fanout:int;budget_tokens:int;budget_cost_microunits:int
    def attenuated_from(self,parent:"DelegationEnvelope")->bool:
        return self.parent_agent==parent.child_agent and self.tenant_id==parent.tenant_id and self.workspace_id==parent.workspace_id and set(self.capabilities)<=set(parent.capabilities) and self.max_depth<=parent.max_depth and self.max_fanout<=parent.max_fanout and self.budget_tokens<=parent.budget_tokens and self.budget_cost_microunits<=parent.budget_cost_microunits
