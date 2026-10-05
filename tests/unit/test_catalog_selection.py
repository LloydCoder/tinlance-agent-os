from tinlance_agent_os.catalog_matcher import Match
from tinlance_agent_os.catalog_schema import CapabilityProfile
from tinlance_agent_os.catalog_selection import select
def test_selection_is_deterministic():
 p1=CapabilityProfile(id="b",version="1",domain="x",capability_ids=("x",),provenance=("a",))
 p2=CapabilityProfile(id="a",version="1",domain="x",capability_ids=("x",),provenance=("a",))
 assert select((Match(p1,10,()),Match(p2,10,()))).profile_id=="a"
