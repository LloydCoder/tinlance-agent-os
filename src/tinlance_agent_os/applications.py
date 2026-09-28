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
        required = (
            self.application_id,
            self.name,
            self.version,
            self.min_os_version,
            self.entrypoint,
        )
        if any(not value.strip() for value in required):
            raise ValueError("manifest fields are required")
        capability_ids = [item.capability_id for item in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("duplicate capability request")
        if any(
            not capability.capability_id.strip() or not capability.reason.strip()
            for capability in self.capabilities
        ):
            raise ValueError("invalid capability request")
        if any(not key.strip() or not value.strip() for key, value in self.metadata.items()):
            raise ValueError("manifest metadata must be non-empty")
        if not self.entrypoint.strip() or any(character in self.entrypoint for character in "\x00\r\n"):
            raise ValueError("invalid entrypoint")


@dataclass(slots=True)
class ApplicationRegistry:
    items: dict[str, tuple[AgentManifest, ApplicationState]] = field(default_factory=dict)

    def install(self, manifest: AgentManifest) -> None:
        manifest.validate()
        current = self.items.get(manifest.application_id)
        if current is not None and current[0] != manifest:
            raise ValueError("application is already installed with a different manifest")
        self.items[manifest.application_id] = (manifest, ApplicationState.INSTALLED)

    def enable(self, application_id: str) -> AgentManifest:
        manifest, state = self.items[application_id]
        if state is ApplicationState.UNINSTALLED:
            raise ValueError("uninstalled application cannot be enabled")
        self.items[application_id] = (manifest, ApplicationState.ENABLED)
        return manifest

    def disable(self, application_id: str) -> None:
        manifest, state = self.items[application_id]
        if state is ApplicationState.UNINSTALLED:
            raise ValueError("uninstalled application cannot be disabled")
        self.items[application_id] = (manifest, ApplicationState.DISABLED)

    def uninstall(self, application_id: str) -> None:
        manifest, _ = self.items[application_id]
        self.items[application_id] = (manifest, ApplicationState.UNINSTALLED)
