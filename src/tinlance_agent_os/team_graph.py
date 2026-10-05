"""Executable team DAG adapter; delegates actual runtime to M17."""

from __future__ import annotations

from dataclasses import dataclass

from .team_spec import TeamBudget


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

    def validate_against_budget(self, budget: TeamBudget) -> None:
        self.validate()
        if len(self.nodes) > budget.max_agents:
            raise ValueError("team graph exceeds max_agents")
        if budget.max_fanout:
            for node in self.nodes:
                if len(node.depends_on) > budget.max_fanout:
                    raise ValueError("team graph exceeds max_fanout")
        if budget.max_depth:
            edges = {node.node_id: node.depends_on for node in self.nodes}
            cache: dict[str, int] = {}

            def depth(node_id: str) -> int:
                if node_id in cache:
                    return cache[node_id]
                value = 0 if not edges[node_id] else 1 + max(
                    depth(dependency) for dependency in edges[node_id]
                )
                cache[node_id] = value
                return value

            if max(depth(node.node_id) for node in self.nodes) > budget.max_depth:
                raise ValueError("team graph exceeds max_depth")
