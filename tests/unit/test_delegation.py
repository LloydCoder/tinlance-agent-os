from tinlance_agent_os.delegation import DelegationEnvelope
def test_delegation_only_attenuates():
 p=DelegationEnvelope("root","p","t","w",("a","b"),3,4,100,50)
 c=DelegationEnvelope("p","c","t","w",("a",),2,2,40,20)
 assert c.attenuated_from(p)
