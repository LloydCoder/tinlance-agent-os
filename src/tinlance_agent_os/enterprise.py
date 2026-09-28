"""Remote/fleet abstractions. Local OS never becomes the enterprise authority."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from collections.abc import Sequence
from .transport import PlatformTransport, PlatformRequestContext

class FleetState(StrEnum):
    ONLINE="online"; OFFLINE="offline"; DRAINING="draining"

@dataclass(frozen=True, slots=True)
class RemoteAgent:
    agent_id: str
    endpoint: str
    state: FleetState

@dataclass(slots=True)
class FleetRegistry:
    agents: dict[str,RemoteAgent]
    def register(self, agent: RemoteAgent)->None:
        if not agent.endpoint.startswith(("https://","unix://")): raise ValueError("remote endpoint must be secure")
        self.agents[agent.agent_id]=agent
    def available(self)->Sequence[RemoteAgent]:
        return tuple(a for a in self.agents.values() if a.state is FleetState.ONLINE)
