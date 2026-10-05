from tinlance_agent_os.delegation import DelegationEnvelope


def test_delegation_only_attenuates() -> None:
    parent = DelegationEnvelope("root", "p", "t", "w", ("a", "b"), 3, 4, 100, 50)
    child = DelegationEnvelope("p", "c", "t", "w", ("a",), 2, 2, 40, 20)
    assert child.attenuated_from(parent)
