"""Reference-agent capability profile bindings."""

from __future__ import annotations

from dataclasses import dataclass

from .catalog_schema import CapabilityProfile
from .catalog_store import CatalogStore


@dataclass(frozen=True, slots=True)
class AgentCapabilityBinding:
    agent_id: str
    profile_id: str
    directory_ref: str
    registry_ref: str
    profile_version: str


class AgentProfileCatalog:
    def __init__(self, store: CatalogStore) -> None:
        self.store = store
        self._bindings: dict[str, AgentCapabilityBinding] = {}

    def bind(
        self,
        binding: AgentCapabilityBinding,
        profile: CapabilityProfile,
    ) -> None:
        if binding.profile_id != profile.id or binding.profile_version != profile.version:
            raise ValueError("binding/profile version mismatch")
        if self.store.get(profile.id) is None:
            self.store.upsert(profile)
        self._bindings[binding.agent_id] = binding

    def profile_for(self, agent_id: str) -> CapabilityProfile | None:
        binding = self._bindings.get(agent_id)
        return self.store.get(binding.profile_id) if binding else None
