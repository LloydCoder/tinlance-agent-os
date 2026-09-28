"""Presentation/shell model independent of GUI toolkit."""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Callable

@dataclass(frozen=True, slots=True)
class ShellCommand:
    command_id: str
    title: str
    handler: Callable[[], object]

@dataclass(slots=True)
class AgentShell:
    commands: dict[str,ShellCommand]
    def register(self, command: ShellCommand)->None:
        if command.command_id in self.commands: raise ValueError("duplicate shell command")
        self.commands[command.command_id]=command
    def invoke(self, command_id: str)->object:
        return self.commands[command_id].handler()
