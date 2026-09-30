"""Production/distribution metadata and verified update state machine."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


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
        if not self.version.strip():
            raise ValueError("version is required")
        digest = self.sha256.lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("sha256 must be a 64-character hexadecimal digest")
        parsed = urlparse(self.uri)
        if parsed.scheme not in {"https", "file"} or not parsed.netloc and parsed.scheme == "https":
            raise ValueError("release artifact URI must be https or file")
        if parsed.username is not None or parsed.password is not None or parsed.fragment:
            raise ValueError("release artifact URI must not contain credentials or fragments")
        if self.size < 0:
            raise ValueError("artifact size cannot be negative")

    def verify(self, data: bytes) -> bool:
        return len(data) == self.size and hashlib.sha256(data).hexdigest() == self.sha256.lower()


def _version_key(version: str) -> tuple[int, ...]:
    parts = version.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError("release version must be numeric dot notation")
    return tuple(int(part) for part in parts)


@dataclass(slots=True)
class UpdateManager:
    state: UpdateState = UpdateState.IDLE
    active_version: str = "0.1.0"
    previous_version: str | None = None
    staged_version: str | None = None

    def stage(self, artifact: ReleaseArtifact, data: bytes) -> None:
        if _version_key(artifact.version) <= _version_key(self.active_version):
            raise ValueError("downgrade or same-version update is forbidden")
        self.state = UpdateState.DOWNLOADING
        if not artifact.verify(data):
            self.state = UpdateState.FAILED
            raise ValueError("artifact integrity verification failed")
        self.state = UpdateState.VERIFIED
        self.staged_version = artifact.version
        self.state = UpdateState.STAGED

    def discard_staged(self) -> None:
        """Abort a staged update before activation."""
        if self.state is UpdateState.STAGED:
            self.staged_version = None
            self.state = UpdateState.IDLE

    def apply(self, version: str) -> None:
        if self.state is not UpdateState.STAGED or self.staged_version != version:
            raise RuntimeError("update is not staged for this version")
        self.previous_version = self.active_version
        self.active_version = version
        self.staged_version = None
        self.state = UpdateState.APPLIED

    def rollback(self) -> None:
        if self.previous_version is None:
            raise RuntimeError("no rollback target")
        self.active_version, self.previous_version = (
            self.previous_version,
            self.active_version,
        )
        self.staged_version = None
        self.state = UpdateState.ROLLED_BACK
