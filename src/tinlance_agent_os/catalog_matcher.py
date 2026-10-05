"""Reproducible capability matching; no authorization decisions."""
from __future__ import annotations
from dataclasses import dataclass
from .catalog_schema import CapabilityProfile
@dataclass(frozen=True,slots=True)
class MatchRequirement:
    capabilities: frozenset[str]
    domain: str|None=None
    tools: frozenset[str]=frozenset()
    environments: frozenset[str]=frozenset()
    protocols: frozenset[str]=frozenset()
@dataclass(frozen=True,slots=True)
class Match:
    profile: CapabilityProfile
    score: float
    reasons: tuple[str,...]
def match_profile(p:CapabilityProfile,r:MatchRequirement)->Match|None:
    caps=set(p.capability_ids)
    if not r.capabilities.issubset(caps) or (r.domain and p.domain!=r.domain): return None
    missing_tools=r.tools-set(p.tools); missing_env=r.environments-set(p.environments); missing_proto=r.protocols-set(p.protocols)
    if missing_tools or missing_env or missing_proto: return None
    score=len(r.capabilities)*10+len(r.tools)*2+len(r.environments)*2+len(r.protocols)*2
    return Match(p,float(score),("capabilities","domain","tools","environments","protocols"))
