from tinlance_agent_os.applications import AgentManifest, CapabilityRequest
from tinlance_agent_os.distribution import ReleaseArtifact
from tinlance_agent_os.enterprise import FleetRegistry, RemoteAgent, FleetState


def test_application_manifest_is_declarative() -> None:
    manifest = AgentManifest(
        "id",
        "name",
        "1",
        "0",
        "entry",
        (CapabilityRequest("cap", "reason"),),
    )
    manifest.validate()


def test_remote_registry_requires_secure_endpoint() -> None:
    registry = FleetRegistry({})
    registry.register(
        RemoteAgent("a", "https://example.invalid", FleetState.ONLINE)
    )
    assert len(registry.available()) == 1


def test_release_artifact_is_content_addressed() -> None:
    assert ReleaseArtifact(
        "1",
        "0" * 64,
        0,
        "https://example.invalid",
    ).verify(b"") is False
