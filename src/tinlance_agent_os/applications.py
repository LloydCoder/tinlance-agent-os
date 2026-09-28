"""Declarative agent application manifest and lifecycle model."""
from dataclasses import dataclass, field
from enum import StrEnum



class ApplicationState(StrEnum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    FAILED = "failed"
    UNINSTALLED = "uninstalled"



@dataclass(frozen=True, slots=True)
class CapabilityRequest:
    capability_id: str
    reason: str
    optional: bool = False



@dataclass(frozen=True, slots=True)
class AgentManifest:
    application_id: str
    name: str
    version: str
    min_os_version: str
    entrypoint: str
    capabilities: tuple[CapabilityRequest, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.application_id,
                self.name,
                self.version,
                self.min_os_version,
                self.entrypoint,
            )
        ):
            raise ValueError("manifest fields are required")
        if any(
            not capability.capability_id.strip() or not capability.reason.strip()
            for capability in self.capabilities
        ):
            raise ValueError("invalid capability request")



@dataclass(slots=True)
class ApplicationRegistry:
    items: dict[str, tuple[AgentManifest, ApplicationState]] = field(default_factory=dict)

    def install(self, manifest: AgentManifest) -> None:
        manifest.validate()
        self.items[manifest.application_id] = (
            manifest,
            ApplicationState.INSTALLED,
        )

    def enable(self, application_id: str) -> AgentManifest:
        manifest, _ = self.items[application_id]
        self.items[application_id] = (manifest, ApplicationState.ENABLED)
        return manifest

    def disable(self, application_id: str) -> None:
        manifest, _ = self.items[application_id]
        self.items[application_id] = (manifest, ApplicationState.DISABLED)
