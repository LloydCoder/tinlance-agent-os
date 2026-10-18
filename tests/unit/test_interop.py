import pytest

from tinlance_agent_os.interop import from_a2a_card, from_mcp_metadata


def test_protocol_adapters_remain_descriptive_and_accept_canonical_shapes() -> None:
    a2a = from_a2a_card(
        {
            "name": "research-agent",
            "protocolVersion": "1.0",
            "supportedInterfaces": [
                {
                    "url": "https://agent.example.test/a2a",
                    "protocolBinding": "JSONRPC",
                    "protocolVersion": "1.0",
                }
            ],
            "capabilities": {"streaming": True, "pushNotifications": False},
            "skills": [{"id": "research", "name": "Research"}],
            "securitySchemes": {"bearer": {"httpAuthSecurityScheme": {"scheme": "Bearer"}}},
            "provider": {"organization": "Tinlance"},
        }
    )
    mcp = from_mcp_metadata(
        {
            "protocolVersion": "2026-07-28",
            "serverInfo": {"name": "tinlance-research", "version": "1.0.0"},
            "endpoint": "https://mcp.example.test/mcp",
            "capabilities": {"tools": {}},
            "tools": [{"name": "search"}, {"name": "fetch"}],
            "securitySchemes": {"oauth2": {}},
        }
    )
    assert a2a.protocol == "a2a"
    assert a2a.endpoint == "https://agent.example.test/a2a"
    assert a2a.capabilities == ("streaming",)
    assert a2a.skills == ("research",)
    assert a2a.security_schemes == ("bearer",)
    assert a2a.provenance == "Tinlance"
    assert mcp.protocol == "mcp"
    assert mcp.capabilities == ("fetch", "search")
    assert mcp.security_schemes == ("oauth2",)


@pytest.mark.parametrize(
    "endpoint",
    (
        "http://agent.example.test/a2a",
        "https://user:password@agent.example.test/a2a",
        "https://agent.example.test/a2a?token=unsafe",
        "https://agent.example.test/a2a#fragment",
        "https://localhost/a2a",
        "https://127.0.0.1/a2a",
        "https://10.0.0.8/a2a",
    ),
)
def test_protocol_profiles_reject_unsafe_remote_endpoints(endpoint: str) -> None:
    with pytest.raises(ValueError):
        from_a2a_card(
            {
                "version": "1.0",
                "url": endpoint,
                "skills": ["research"],
            }
        )


def test_protocol_adapters_reject_malformed_metadata() -> None:
    with pytest.raises(ValueError):
        from_a2a_card(
            {"version": "1.0", "url": "https://agent.example.test/a2a", "skills": "research"}
        )
    with pytest.raises(ValueError):
        from_mcp_metadata(
            {
                "protocolVersion": "2026-07-28",
                "serverInfo": {"name": "research"},
                "endpoint": "https://mcp.example.test/mcp",
                "tools": [{"name": "search"}, {"name": "search"}],
            }
        )


@pytest.mark.parametrize("version", ("2024-11-05", "2026-99-99"))
def test_mcp_metadata_rejects_unsupported_protocol_versions(version: str) -> None:
    with pytest.raises(ValueError, match="unsupported MCP protocol version"):
        from_mcp_metadata(
            {
                "protocolVersion": version,
                "serverInfo": {"name": "research", "version": "1.0.0"},
                "endpoint": "https://mcp.example.test/mcp",
                "tools": [{"name": "search"}],
            }
        )


def test_mcp_metadata_rejects_blank_protocol_version() -> None:
    with pytest.raises(ValueError, match="normalized non-empty string"):
        from_mcp_metadata(
            {
                "protocolVersion": "",
                "serverInfo": {"name": "research", "version": "1.0.0"},
                "endpoint": "https://mcp.example.test/mcp",
                "tools": [{"name": "search"}],
            }
        )


def test_a2a_card_rejects_unsupported_wire_protocol_version() -> None:
    with pytest.raises(ValueError, match="unsupported A2A protocol version"):
        from_a2a_card(
            {
                "name": "research-agent",
                "supportedInterfaces": [
                    {
                        "url": "https://agent.example.test/a2a",
                        "protocolBinding": "JSONRPC",
                        "protocolVersion": "2.0",
                    }
                ],
                "skills": [{"id": "research", "name": "Research"}],
                "securitySchemes": {
                    "bearer": {"httpAuthSecurityScheme": {"scheme": "Bearer"}}
                },
            }
        )
