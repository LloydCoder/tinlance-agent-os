"""System integration abstractions with explicit local boundaries."""
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
        executable = Path(argv[0]).name
        if executable not in self.allowed_commands:
            raise PermissionError("process execution is not permitted by local policy")
        return subprocess.run(
            argv,
            check=False,
            timeout=timeout,
            cwd=self.root,
        ).returncode
