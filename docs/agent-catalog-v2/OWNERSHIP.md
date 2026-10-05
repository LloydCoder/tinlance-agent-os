
# Agent Catalog v2 Ownership and Trust Matrix

| Artifact/decision | OS | Platform | M26 | M36 | Catalog | M17 | FAS |
|---|---|---|---|---|---|---|---|
| Agent identity | integrate | authoritative | reference | publisher ref | profile ref | authenticate | reference |
| Desired agent state | observe | enforce | authoritative | no | reference | no | no |
| Package/version trust | reference | enforce at execution | reference | authoritative | consume | no | no |
| Capability semantics | host | authorize | reference | package metadata | authoritative | consume | reference |
| Agent discovery | expose | no | inventory | package discovery | authoritative | consume | no |
| Team composition | planner | authorize | no | no | plan | coordinate | evidence refs |
| Team execution | lifecycle | authoritative | no | no | no | coordinate | evidence |
| Delegation authority | propose | authoritative | no | no | constrain | carry | no |
| Policy | consume | authoritative | no | no | describe constraints | consume | no |
| Approval | request/reference | authoritative | no | no | no | carry refs | no |
| Evidence | present refs | authoritative | no | provenance ref | reference | carry refs | analyze |
| Finding/verdict | no | evidence boundary | no | no | no | no | analysis semantics |
| Protocol metadata | integrate | security boundary | no | package metadata | normalize | transport | no |

## Trust boundary

~~~text
Untrusted metadata
      |
      v
Catalog validation / provenance / evaluation
      |
      v
Candidate selection
      |
      v
Platform identity + authorization + policy
      |
      v
Approval when required
      |
      v
Platform governed execution
      |
      v
Authoritative evidence/audit
~~~

Catalog data must never be treated as proof that a consequential action is permitted.
