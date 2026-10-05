"""Protocol-neutral external agent/tool metadata adapters."""
from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class ProtocolProfile:
    protocol:str;version:str;endpoint:str;capabilities:tuple[str,...]=();skills:tuple[str,...]=();security_schemes:tuple[str,...]=();provenance:str=""
def from_a2a_card(card:dict[str,object])->ProtocolProfile:
    return ProtocolProfile("a2a",str(card.get("version","unknown")),str(card.get("url","")),tuple(card.get("capabilities",()) or ()),tuple(card.get("skills",()) or ()),tuple(card.get("securitySchemes",()) or ()),str(card.get("provider","")))
def from_mcp_metadata(meta:dict[str,object])->ProtocolProfile:
    return ProtocolProfile("mcp",str(meta.get("version","unknown")),str(meta.get("endpoint","")),tuple(meta.get("tools",()) or ()),(),tuple(meta.get("securitySchemes",()) or ()),str(meta.get("server","")))
