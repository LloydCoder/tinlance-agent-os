"""Remote/fleet integration seams above the Platform authority plane."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class FleetState(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    DRAINING = "draining"


@dataclass(frozen=True, slots=True)
class RemoteAgent:
    agent_id: str
    endpoint: str
    state: FleetState


@dataclass(slots=True)
class FleetRegistry:
    agents: dict[str, RemoteAgent]

    def register(self, agent: RemoteAgent) -> None:
        if not agent.endpoint.startswith(("https://", "unix://")):
            raise ValueError("remote endpoint must use a secure scheme")
        self.agents[agent.agent_id] = agent

    def available(self) -> Sequence[RemoteAgent]:
        return tuple(
            agent
            for agent in self.agents.values()
            if agent.state is FleetState.ONLINE
        )
