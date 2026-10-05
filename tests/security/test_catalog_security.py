from tinlance_agent_os.catalog_security import REQUIRED_SCENARIOS,validate_security_suite
def test_required_agentic_security_suite(): validate_security_suite();assert len(REQUIRED_SCENARIOS)>=10
