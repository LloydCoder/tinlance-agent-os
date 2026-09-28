"""Production/distribution metadata and safe update state machine."""

import hashlib
from dataclasses import dataclass
from enum import StrEnum



class UpdateState(StrEnum):
    IDLE = "idle"
    DOWNLOADING = "downloading"
    VERIFIED = "verified"
    STAGED = "staged"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"



@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    version: str
    sha256: str
    size: int
    uri: str

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256.lower()
        ):
            raise ValueError("sha256 must be a 64-character hexadecimal digest")
        if self.size < 0 or not self.uri.startswith(("https://", "file://")):
            raise ValueError("invalid release artifact metadata")

    def verify(self, data: bytes) -> bool:
        return (
            len(data) == self.size
            and hashlib.sha256(data).hexdigest() == self.sha256.lower()
        )



@dataclass(slots=True)
class UpdateManager:
    state: UpdateState = UpdateState.IDLE
    active_version: str = "0.1.0"
    previous_version: str | None = None

    def stage(self, artifact: ReleaseArtifact, data: bytes) -> None:
        self.state = UpdateState.DOWNLOADING
        if not artifact.verify(data):
            self.state = UpdateState.FAILED
            raise ValueError("artifact integrity verification failed")
        self.state = UpdateState.VERIFIED
        self.state = UpdateState.STAGED

    def apply(self, version: str) -> None:
        if self.state is not UpdateState.STAGED:
            raise RuntimeError("update is not staged")
        if not version.strip():
            raise ValueError("version is required")
        self.previous_version = self.active_version
        self.active_version = version
        self.state = UpdateState.APPLIED

    def rollback(self) -> None:
        if self.previous_version is None:
            raise RuntimeError("no rollback target")
        self.active_version, self.previous_version = (
            self.previous_version,
            self.active_version,
        )
        self.state = UpdateState.ROLLED_BACK
