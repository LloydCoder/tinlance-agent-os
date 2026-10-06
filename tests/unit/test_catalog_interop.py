import pytest

from tinlance_agent_os.catalog_interop import (
    InteropProtocol,
    InteropMapping,
    map_a2a_agent_card,
    map_mcp_server,
)


def test_a2a_mapping_is_descriptive_and_deterministic() -> None:
    mapping = map_a2a_agent_card(
        name="Threat Intelligence Agent",
        version="1.0",
        capabilities=("threat-intelligence",),
        skills=("ioc-correlation",),
        interfaces=("https://agent.example/a2a/v1",),
        security_schemes=("oauth2",),
        signed=True,
    )
    assert mapping.protocol is InteropProtocol.A2A
    assert mapping.provider_type == "agent"
    assert mapping.signed is True
    assert len(mapping.fingerprint) == 64


def test_mcp_is_never_classified_as_an_agent() -> None:
    mapping = map_mcp_server(
        name="Security Tools",
        version="1.0",
        tools=("scanner",),
        resources=("findings",),
        prompts=("summarize",),
        interface="https://tools.example/mcp",
    )
    assert mapping.protocol is InteropProtocol.MCP
    assert mapping.provider_type == "tool-provider"
    assert "tool:scanner" in mapping.capabilities
    assert "resource:findings" in mapping.capabilities
    assert "prompt:summarize" in mapping.skills


@pytest.mark.parametrize(
    "interface",
    ["http://agent.example/a2a", "ftp://agent.example/a2a", "agent.example/a2a"],
)
def test_production_interfaces_fail_closed(interface: str) -> None:
    with pytest.raises(ValueError, match="HTTPS or gRPC"):
        map_a2a_agent_card(
            name="Agent",
            version="1.0",
            capabilities=("capability",),
            skills=("skill",),
            interfaces=(interface,),
        )


def test_a2a_requires_skill_metadata() -> None:
    with pytest.raises(ValueError, match="descriptive skill"):
        map_a2a_agent_card(
            name="Agent",
            version="1.0",
            capabilities=("capability",),
            skills=(),
            interfaces=("https://agent.example/a2a/v1",),
        )


def test_mcp_cannot_change_provider_class() -> None:
    with pytest.raises(ValueError, match="tool-provider"):
        InteropMapping(
            protocol=InteropProtocol.MCP,
            protocol_version="1.0",
            identity="server",
            capabilities=("tool:scanner",),
            skills=("mcp:provider",),
            input_modes=(),
            output_modes=(),
            interfaces=("https://tools.example/mcp",),
            security_schemes=(),
            signed=False,
            provider_type="agent",
        )
