"""Executable team DAG adapter; delegates actual runtime to M17."""
from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class TeamNode:
    node_id:str;agent_id:str;depends_on:tuple[str,...]=()
@dataclass(frozen=True,slots=True)
class TeamGraph:
    nodes:tuple[TeamNode,...]
    def validate(self)->None:
        ids={n.node_id for n in self.nodes}
        if len(ids)!=len(self.nodes): raise ValueError("duplicate team node")
        for n in self.nodes:
            if any(d not in ids for d in n.depends_on): raise ValueError("unknown dependency")
            if n.node_id in n.depends_on: raise ValueError("self dependency")
        visiting:set[str]=set();done:set[str]=set()
        edges={n.node_id:n.depends_on for n in self.nodes}
        def visit(x:str)->None:
            if x in visiting: raise ValueError("cycle")
            if x in done:return
            visiting.add(x)
            for d in edges[x]:visit(d)
            visiting.remove(x);done.add(x)
        for x in ids:visit(x)
