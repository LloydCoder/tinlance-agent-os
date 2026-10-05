from tinlance_agent_os.catalog_matcher import *
from tinlance_agent_os.catalog_schema import CapabilityProfile
def test_match_is_reproducible():
 p=CapabilityProfile(id="a",version="1",domain="security",capability_ids=("scan","report"),tools=("github",),provenance=("x",))
 r=MatchRequirement(frozenset(("scan",)),domain="security",tools=frozenset(("github",)))
 m=match_profile(p,r);assert m and m.score==12.0
