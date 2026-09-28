from tinlance_agent_os.client import ReferenceAgentPlatformClient
from tinlance_agent_os.contracts import AgentPlatformClient


def test_reference_client_implements_platform_contract() -> None:
    client: AgentPlatformClient = ReferenceAgentPlatformClient()
    assert client.health()
    assert client.get_principal().user_id
