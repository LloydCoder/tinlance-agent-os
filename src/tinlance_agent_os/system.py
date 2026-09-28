"""System integration abstractions; implementations remain outside authority plane."""
from __future__ import annotations
import os, subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

class SystemBackend(Protocol):
    def read_file(self, path: Path) -> bytes: ...
    def write_file(self, path: Path, data: bytes) -> None: ...
    def notify(self, title: str, body: str) -> None: ...
    def run_process(self, argv: list[str], timeout: float=10.0) -> int: ...

@dataclass(frozen=True, slots=True)
class LocalSystemBackend:
    root: Path
    def _safe(self,path: Path)->Path:
        resolved=(self.root/path).resolve()
        if self.root.resolve() not in resolved.parents and resolved!=self.root.resolve(): raise PermissionError("path escapes system root")
        return resolved
    def read_file(self,path:Path)->bytes: return self._safe(path).read_bytes()
    def write_file(self,path:Path,data:bytes)->None:
        target=self._safe(path); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
    def notify(self,title:str,body:str)->None: return
    def run_process(self,argv:list[str],timeout:float=10.0)->int:
        if not argv or any(not x or "\x00" in x for x in argv): raise ValueError("invalid argv")
        return subprocess.run(argv,check=False,timeout=timeout,cwd=self.root).returncode
