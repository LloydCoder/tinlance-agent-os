import pytest
from tinlance_agent_os.catalog_trust import (
    AutonomyClass,
    DataSensitivity,
    RiskClass,
    SecurityTrustProfile,
    classify_security_trust,
)

def base(**overrides: object) -> SecurityTrustProfile:
    values: dict[str, object] = {
        "risk_class": RiskClass.MEDIUM,
        "autonomy_class": AutonomyClass.SUPERVISED,
        "data_sensitivity": DataSensitivity.INTERNAL,
        "write_capable": False,
        "network_access": True,
        "credential_required": False,
        "destructive_action_potential": False,
        "human_approval_required": False,
        "evidence_required": True,
        "isolation_required": False,
    }
    values.update(overrides)
    return SecurityTrustProfile(**values)

def test_classification_is_deterministic() -> None:
    first = base()
    second = classify_security_trust(**{
        "risk_class": RiskClass.MEDIUM,
        "autonomy_class": AutonomyClass.SUPERVISED,
        "data_sensitivity": DataSensitivity.INTERNAL,
        "write_capable": False,
        "network_access": True,
        "credential_required": False,
        "destructive_action_potential": False,
        "human_approval_required": False,
        "evidence_required": True,
        "isolation_required": False,
    })
    assert first == second
    assert len(first.fingerprint) == 64

@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"risk_class": RiskClass.LOW, "destructive_action_potential": True}, "destructive"),
        ({"risk_class": RiskClass.LOW, "data_sensitivity": DataSensitivity.RESTRICTED}, "restricted"),
        ({"autonomy_class": AutonomyClass.AUTONOMOUS, "evidence_required": False}, "evidence"),
        (\n            {"destructive_action_potential": True, "risk_class": RiskClass.HIGH, "isolation_required": True},\n            "human approval",\n        ),
        ({"credential_required": True, "network_access": False}, "network access"),
        ({"risk_class": RiskClass.HIGH}, "isolation"),
    ],
)
def test_classification_fails_closed(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        base(**overrides)
