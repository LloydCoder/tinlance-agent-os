"""Remote/fleet integration seams above the Platform authority plane."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


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
        parsed = urlparse(agent.endpoint)
        if parsed.scheme not in {"https", "unix"} or not parsed.netloc:
            raise ValueError("remote endpoint must use https or unix with a non-empty authority")
        if parsed.username is not None or parsed.password is not None or parsed.fragment:
            raise ValueError("remote endpoint must not contain credentials or fragments")
        if not agent.agent_id.strip():
            raise ValueError("agent_id is required")
        self.agents[agent.agent_id] = agent

    def available(self) -> Sequence[RemoteAgent]:
        return tuple(agent for agent in self.agents.values() if agent.state is FleetState.ONLINE)
