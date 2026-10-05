"""Executable team DAG adapter; delegates actual runtime to M17."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TeamNode:
    node_id: str
    agent_id: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TeamGraph:
    nodes: tuple[TeamNode, ...]

    def validate(self) -> None:
        ids = {node.node_id for node in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("duplicate team node")

        for node in self.nodes:
            if any(dependency not in ids for dependency in node.depends_on):
                raise ValueError("unknown dependency")
            if node.node_id in node.depends_on:
                raise ValueError("self dependency")

        visiting: set[str] = set()
        done: set[str] = set()
        edges = {node.node_id: node.depends_on for node in self.nodes}

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("cycle")
            if node_id in done:
                return
            visiting.add(node_id)
            for dependency in edges[node_id]:
                visit(dependency)
            visiting.remove(node_id)
            done.add(node_id)

        for node_id in ids:
            visit(node_id)
