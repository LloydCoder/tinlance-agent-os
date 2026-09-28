"""Production/distribution metadata and safe update state machine."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import hashlib

class UpdateState(StrEnum):
    IDLE="idle"; DOWNLOADING="downloading"; VERIFIED="verified"; STAGED="staged"; APPLIED="applied"; ROLLED_BACK="rolled_back"; FAILED="failed"

@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    version: str
    sha256: str
    size: int
    uri: str
    def verify(self,data:bytes)->bool:
        return len(data)==self.size and hashlib.sha256(data).hexdigest()==self.sha256

@dataclass(slots=True)
class UpdateManager:
    state: UpdateState=UpdateState.IDLE
    active_version: str="0.1.0"
    previous_version: str|None=None
    def stage(self, artifact: ReleaseArtifact, data: bytes)->None:
        if not artifact.verify(data): self.state=UpdateState.FAILED; raise ValueError("artifact integrity verification failed")
        self.state=UpdateState.STAGED
    def apply(self, version: str)->None:
        if self.state is not UpdateState.STAGED: raise RuntimeError("update is not staged")
        self.previous_version=self.active_version; self.active_version=version; self.state=UpdateState.APPLIED
    def rollback(self)->None:
        if self.previous_version is None: raise RuntimeError("no rollback target")
        self.active_version,self.previous_version=self.previous_version,self.active_version; self.state=UpdateState.ROLLED_BACK
