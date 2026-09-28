"""Capability-scoped extension SDK."""
from dataclasses import dataclass
from typing import Protocol

from .applications import AgentManifest



class Extension(Protocol):
    def start(self, context: "ExtensionContext") -> None: ...

    def stop(self) -> None: ...



@dataclass(frozen=True, slots=True)
class ExtensionContext:
    application_id: str
    granted_capabilities: frozenset[str]

    def require(self, capability: str) -> None:
        if capability not in self.granted_capabilities:
            raise PermissionError("capability not granted")



@dataclass(slots=True)
class ExtensionManager:
    extensions: dict[str, Extension]

    def load(
        self,
        manifest: AgentManifest,
        extension: Extension,
        granted_capabilities: frozenset[str],
    ) -> None:
        manifest.validate()
        requested = {item.capability_id for item in manifest.capabilities}
        if not granted_capabilities <= requested:
            raise ValueError("grant exceeds declared request")
        extension.start(
            ExtensionContext(manifest.application_id, granted_capabilities)
        )
        self.extensions[manifest.application_id] = extension

    def unload(self, application_id: str) -> None:
        extension = self.extensions.pop(application_id)
        extension.stop()
