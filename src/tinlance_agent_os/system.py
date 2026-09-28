"""System integration abstractions with explicit local boundaries."""

from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class SystemBackend(Protocol):
    def read_file(self, path: Path) -> bytes: ...

    def write_file(self, path: Path, data: bytes) -> None: ...

    def notify(self, title: str, body: str) -> None: ...

    def run_process(self, argv: list[str], timeout: float = 10.0) -> int: ...


@dataclass(frozen=True, slots=True)
class LocalSystemBackend:
    """Constrained local integration; Platform remains the authority for consequential actions."""

    root: Path
    allowed_commands: frozenset[str] = frozenset()

    def _safe(self, path: Path) -> Path:
        root = self.root.resolve()
        resolved = (root / path).resolve()
        if root not in resolved.parents and resolved != root:
            raise PermissionError("path escapes system root")
        return resolved

    def read_file(self, path: Path) -> bytes:
        return self._safe(path).read_bytes()

    def write_file(self, path: Path, data: bytes) -> None:
        target = self._safe(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def notify(self, title: str, body: str) -> None:
        del title, body

    def run_process(self, argv: list[str], timeout: float = 10.0) -> int:
        if not argv or any(not value or "\x00" in value for value in argv):
            raise ValueError("invalid argv")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        executable = Path(argv[0])
        if executable.is_absolute() or executable.parent != Path("."):
            raise PermissionError("only allowlisted executable names are permitted")
        command = executable.name
        if command not in self.allowed_commands:
            raise PermissionError("process execution is not permitted by local policy")
        resolved = self._resolve_allowlisted_command(command)
        try:
            process = subprocess.Popen(
                [str(resolved), *argv[1:]],
                cwd=self.root,
                env={"PATH": "/usr/bin:/bin"},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
            try:
                return process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=1)
                raise
        except FileNotFoundError as exc:
            raise PermissionError("allowlisted executable is unavailable") from exc

    @staticmethod
    def _resolve_allowlisted_command(command: str) -> Path:
        for directory in (Path("/usr/bin"), Path("/bin"), Path("/usr/local/bin")):
            candidate = directory / command
            try:
                resolved = candidate.resolve(strict=True)
            except FileNotFoundError:
                continue
            if resolved.is_file() and os.access(resolved, os.X_OK):
                return resolved
        raise PermissionError("allowlisted executable could not be resolved")
