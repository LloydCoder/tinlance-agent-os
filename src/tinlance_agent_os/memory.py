"""Secure, durable agent memory and context assembly (M15).

Memory is security-sensitive state, not an implicit instruction channel.
Every persisted item carries workspace/scope identity, provenance, classification,
trust, version, lifecycle state and an integrity digest.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import StateStore
from .observability import telemetry


class MemoryError(RuntimeError):
    """Base memory subsystem error."""


class MemoryValidationError(MemoryError, ValueError):
    """A memory contract failed validation."""


class MemoryConflictError(MemoryError):
    """A concurrent or stale memory version was rejected."""


class MemoryAccessError(MemoryError, PermissionError):
    """Memory retrieval crossed an enforced boundary."""


class MemoryScope(StrEnum):
    WORKING = "working"
    SESSION = "session"
    TASK = "task"
    AGENT = "agent"
    LONG_TERM = "long_term"


class MemoryClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class MemoryTrust(StrEnum):
    TRUSTED_INSTRUCTION = "trusted_instruction"
    VERIFIED_FACT = "verified_fact"
    UNTRUSTED_CONTENT = "untrusted_content"
    QUARANTINED = "quarantined"


class MemoryState(StrEnum):
    ACTIVE = "active"
    QUARANTINED = "quarantined"
    EXPIRED = "expired"
    DELETED = "deleted"


class MemorySourceType(StrEnum):
    SYSTEM = "system"
    USER = "user"
    PLATFORM = "platform"
    AGENT = "agent"
    EXTERNAL = "external"
    IMPORT = "import"


class MemoryConflictPolicy(StrEnum):
    REJECT = "reject"
    REPLACE = "replace"


_CLASSIFICATION_RANK = {
    MemoryClassification.PUBLIC: 0,
    MemoryClassification.INTERNAL: 1,
    MemoryClassification.CONFIDENTIAL: 2,
    MemoryClassification.RESTRICTED: 3,
}

_POISON_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+)?previous\s+instructions\b", re.I),
    re.compile(r"\bdisregard\s+(?:all\s+)?prior\s+(?:instructions|rules)\b", re.I),
    re.compile(r"\b(?:system|developer)\s+prompt\b.*\b(?:reveal|print|show|leak)\b", re.I | re.S),
    re.compile(
        r"\b(?:exfiltrat|leak|steal)\w*\b.*\b(?:secret|credential|token|password|key)\b",
        re.I | re.S,
    ),
    re.compile(r"\bdisable\s+(?:security|safety|approval|policy)\b", re.I),
    re.compile(r"\bapprove\s+(?:this|the)\s+(?:action|tool|request)\b", re.I),
    re.compile(
        r"\bcall\s+(?:the\s+)?(?:tool|api)\b.*\bwithout\s+(?:approval|authorization)\b",
        re.I | re.S,
    ),
    re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----", re.I),
    re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs]|AKIA)[A-Za-z0-9_\-]{12,}\b"),
)


@dataclass(frozen=True, slots=True)
class MemoryProvenance:
    source_type: MemorySourceType
    source_id: str
    actor_id: str | None = None
    origin: str | None = None
    collected_at: datetime | None = None
    parent_digest: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise MemoryValidationError("provenance source_id is required")
        if self.actor_id is not None and not self.actor_id.strip():
            raise MemoryValidationError("provenance actor_id cannot be blank")
        if self.origin is not None and not self.origin.strip():
            raise MemoryValidationError("provenance origin cannot be blank")
        if self.collected_at is not None and self.collected_at.tzinfo is None:
            raise MemoryValidationError("provenance collected_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class MemoryWrite:
    workspace_id: str
    scope: MemoryScope
    scope_id: str
    agent_id: str
    content: str
    provenance: MemoryProvenance
    classification: MemoryClassification = MemoryClassification.INTERNAL
    trust: MemoryTrust = MemoryTrust.UNTRUSTED_CONTENT
    memory_key: str | None = None
    session_id: str | None = None
    task_id: str | None = None
    ttl_seconds: int | None = None
    expires_at: datetime | None = None
    expected_version: int | None = None
    conflict_policy: MemoryConflictPolicy = MemoryConflictPolicy.REJECT

    def validate(self) -> None:
        for name, value in (
            ("workspace_id", self.workspace_id),
            ("scope_id", self.scope_id),
            ("agent_id", self.agent_id),
            ("content", self.content),
        ):
            if not value.strip():
                raise MemoryValidationError(f"{name} is required")
        if len(self.content) > 1_000_000:
            raise MemoryValidationError("memory content exceeds 1 MiB")
        if self.memory_key is not None and (
            not self.memory_key.strip() or len(self.memory_key) > 255
        ):
            raise MemoryValidationError("memory_key must be 1-255 characters")
        if self.ttl_seconds is not None and self.ttl_seconds <= 0:
            raise MemoryValidationError("ttl_seconds must be positive")
        if self.ttl_seconds is not None and self.expires_at is not None:
            raise MemoryValidationError("provide ttl_seconds or expires_at, not both")
        if self.expected_version is not None and self.expected_version < 0:
            raise MemoryValidationError("expected_version cannot be negative")
        if self.scope == MemoryScope.SESSION and self.session_id != self.scope_id:
            raise MemoryValidationError("session memory scope_id must equal session_id")
        if self.scope == MemoryScope.TASK and self.task_id != self.scope_id:
            raise MemoryValidationError("task memory scope_id must equal task_id")
        if self.scope == MemoryScope.AGENT and self.scope_id != self.agent_id:
            raise MemoryValidationError("agent memory scope_id must equal agent_id")
        if self.scope == MemoryScope.LONG_TERM and self.scope_id != self.workspace_id:
            raise MemoryValidationError("long-term scope_id must equal workspace_id")


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    memory_id: str
    workspace_id: str
    scope: MemoryScope
    scope_id: str
    agent_id: str
    memory_key: str
    content: str
    classification: MemoryClassification
    trust: MemoryTrust
    state: MemoryState
    version: int
    provenance: MemoryProvenance
    content_digest: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    deleted_at: datetime | None
    quarantine_reason: str | None = None


@dataclass(frozen=True, slots=True)
class MemoryRetrieval:
    query: str
    workspace_id: str
    agent_id: str
    session_id: str | None = None
    task_id: str | None = None
    max_classification: MemoryClassification = MemoryClassification.INTERNAL
    scopes: tuple[MemoryScope, ...] = (MemoryScope.AGENT, MemoryScope.LONG_TERM)
    include_untrusted: bool = True
    include_quarantined: bool = False
    limit: int = 20

    def validate(self) -> None:
        if not self.workspace_id.strip() or not self.agent_id.strip():
            raise MemoryValidationError("workspace_id and agent_id are required")
        if self.limit < 1 or self.limit > 100:
            raise MemoryValidationError("limit must be between 1 and 100")
        if MemoryScope.SESSION in self.scopes and self.session_id is None:
            raise MemoryValidationError("session scope requires session_id")
        if MemoryScope.TASK in self.scopes and self.task_id is None:
            raise MemoryValidationError("task scope requires task_id")


@dataclass(frozen=True, slots=True)
class ContextItem:
    memory_id: str
    content: str
    scope: MemoryScope
    classification: MemoryClassification
    trust: MemoryTrust
    provenance: MemoryProvenance
    version: int


@dataclass(frozen=True, slots=True)
class AssembledContext:
    trusted_instructions: tuple[ContextItem, ...]
    trusted_facts: tuple[ContextItem, ...]
    untrusted_content: tuple[ContextItem, ...]
    quarantined: tuple[ContextItem, ...]
    total_items: int


def _digest(
    *,
    workspace_id: str,
    scope: MemoryScope,
    scope_id: str,
    agent_id: str,
    memory_key: str,
    version: int,
    content: str,
    provenance: MemoryProvenance,
    collected_at: datetime,
) -> str:
    canonical = json.dumps(
        {
            "workspace_id": workspace_id,
            "scope": scope.value,
            "scope_id": scope_id,
            "agent_id": agent_id,
            "memory_key": memory_key,
            "version": version,
            "content": content,
            "provenance": {
                "source_type": provenance.source_type.value,
                "source_id": provenance.source_id,
                "actor_id": provenance.actor_id,
                "origin": provenance.origin,
                "collected_at": (provenance.collected_at or collected_at).isoformat(),
                "parent_digest": provenance.parent_digest,
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _poison_reasons(content: str) -> tuple[str, ...]:
    return tuple(
        f"pattern:{index}"
        for index, pattern in enumerate(_POISON_PATTERNS, start=1)
        if pattern.search(content)
    )


def _effective_expiry(write: MemoryWrite, now: datetime) -> datetime:
    if write.expires_at is not None:
        return write.expires_at.astimezone(UTC)
    if write.ttl_seconds is not None:
        return now + timedelta(seconds=write.ttl_seconds)
    defaults = {
        MemoryScope.WORKING: 3600,
        MemoryScope.SESSION: 86400,
        MemoryScope.TASK: 604800,
        MemoryScope.AGENT: 2592000,
        MemoryScope.LONG_TERM: 7776000,
    }
    return now + timedelta(seconds=defaults[write.scope])


# Backward-compatible M0-M11 name. New code should use MemoryClassification.
DataClassification = MemoryClassification


class MemoryStore:
    """Security-aware memory API over the durable Agent OS StateStore."""

    def __init__(self, store: StateStore) -> None:
        self.store = store

    def put(
        self,
        write: MemoryWrite | str,
        *legacy_args: object,
        now: datetime | None = None,
    ) -> MemoryRecord:
        if isinstance(write, str):
            if len(legacy_args) != 3:
                raise MemoryValidationError(
                    "legacy memory.put requires workspace, scope, classification and content"
                )
            legacy_workspace = write
            scope = legacy_args[0]
            classification, content = legacy_args[1], legacy_args[2]
            if not isinstance(scope, str):
                raise MemoryValidationError("invalid legacy memory scope")
            if not isinstance(classification, MemoryClassification) or not isinstance(content, str):
                raise MemoryValidationError("invalid legacy memory.put arguments")
            if classification == MemoryClassification.RESTRICTED:
                raise PermissionError(
                    "restricted memory requires an explicit M15 classification ceiling"
                )
            scope_value = {
                "working": MemoryScope.WORKING,
                "session": MemoryScope.SESSION,
                "task": MemoryScope.TASK,
                "agent": MemoryScope.AGENT,
                "long_term": MemoryScope.LONG_TERM,
            }.get(scope, MemoryScope.SESSION)
            scope_id = scope
            write = MemoryWrite(
                legacy_workspace,
                scope_value,
                scope_id,
                "legacy-api",
                content,
                MemoryProvenance(MemorySourceType.IMPORT, f"legacy:{scope}"),
                classification=classification,
                memory_key=hashlib.sha256(f"{scope}:{content}".encode()).hexdigest(),
                session_id=(
                    scope_id if scope_value in {MemoryScope.WORKING, MemoryScope.SESSION} else None
                ),
                task_id=scope_id if scope_value == MemoryScope.TASK else None,
                conflict_policy=MemoryConflictPolicy.REPLACE,
                expected_version=0,
            )
        if not isinstance(write, MemoryWrite):
            raise MemoryValidationError("memory.put requires a MemoryWrite")
        write.validate()
        current_time = (now or datetime.now(UTC)).astimezone(UTC)
        reasons = _poison_reasons(write.content)
        trust = write.trust
        trusted_sources = {
            MemorySourceType.SYSTEM,
            MemorySourceType.PLATFORM,
            MemorySourceType.USER,
        }
        if (
            trust in {MemoryTrust.TRUSTED_INSTRUCTION, MemoryTrust.VERIFIED_FACT}
            and write.provenance.source_type not in trusted_sources
        ):
            trust = MemoryTrust.UNTRUSTED_CONTENT
        state = MemoryState.ACTIVE
        quarantine_reason: str | None = None
        if reasons:
            trust = MemoryTrust.QUARANTINED
            state = MemoryState.QUARANTINED
            quarantine_reason = ";".join(reasons)
        elif trust == MemoryTrust.TRUSTED_INSTRUCTION and write.provenance.source_type not in {
            MemorySourceType.SYSTEM,
            MemorySourceType.PLATFORM,
            MemorySourceType.USER,
        }:
            trust = MemoryTrust.UNTRUSTED_CONTENT

        memory_key = (
            write.memory_key
            or hashlib.sha256(
                f"{write.scope.value}:{write.scope_id}:{write.content}".encode()
            ).hexdigest()
        )
        current = self.store.memory_current(
            workspace_id=write.workspace_id,
            scope=write.scope.value,
            scope_id=write.scope_id,
            memory_key=memory_key,
        )
        if current is not None:
            current_version = int(current["version"])
            if write.expected_version != current_version:
                raise MemoryConflictError(
                    f"memory version conflict: expected {write.expected_version}, "
                    f"found {current_version}"
                )
            if write.conflict_policy == MemoryConflictPolicy.REJECT:
                raise MemoryConflictError("memory update requires REPLACE conflict policy")
            version = current_version + 1
            parent_digest = current["content_digest"]
            provenance = MemoryProvenance(
                write.provenance.source_type,
                write.provenance.source_id,
                write.provenance.actor_id,
                write.provenance.origin,
                write.provenance.collected_at,
                parent_digest,
            )
        else:
            if write.expected_version not in (None, 0):
                raise MemoryConflictError("memory does not exist at the expected version")
            version = 1
            provenance = MemoryProvenance(
                write.provenance.source_type,
                write.provenance.source_id,
                write.provenance.actor_id,
                write.provenance.origin,
                write.provenance.collected_at or current_time,
                write.provenance.parent_digest,
            )

        digest = _digest(
            workspace_id=write.workspace_id,
            scope=write.scope,
            scope_id=write.scope_id,
            agent_id=write.agent_id,
            memory_key=memory_key,
            version=version,
            content=write.content,
            provenance=provenance,
            collected_at=current_time,
        )
        memory_id = hashlib.sha256(
            f"{write.workspace_id}:{write.scope.value}:{write.scope_id}:{memory_key}:{version}".encode()
        ).hexdigest()
        expires_at = _effective_expiry(write, current_time)
        self.store.insert_memory_record(
            (
                memory_id,
                write.workspace_id,
                write.scope.value,
                write.scope_id,
                write.agent_id,
                memory_key,
                write.content,
                write.classification.value,
                trust.value,
                state.value,
                version,
                json.dumps(
                    {
                        "source_type": provenance.source_type.value,
                        "source_id": provenance.source_id,
                        "actor_id": provenance.actor_id,
                        "origin": provenance.origin,
                        "collected_at": (provenance.collected_at or current_time).isoformat(),
                        "parent_digest": provenance.parent_digest,
                    },
                    sort_keys=True,
                ),
                digest,
                current_time.isoformat(),
                current_time.isoformat(),
                expires_at.isoformat() if expires_at else None,
                None,
                quarantine_reason,
            )
        )
        row = self.store.get_memory_record(memory_id)
        if row is None:
            raise MemoryError("memory write did not persist")
        telemetry().record_memory(operation="put", scope=write.scope.value)
        return self._row_to_record(row)

    def get(self, memory_id: str, retrieval: MemoryRetrieval) -> MemoryRecord | None:
        retrieval.validate()
        row = self.store.get_memory_record(memory_id)
        if row is None:
            return None
        record = self._row_to_record(row)
        self._assert_access(record, retrieval)
        if record.state == MemoryState.ACTIVE and (
            record.expires_at is not None and record.expires_at <= datetime.now(UTC)
        ):
            self.store.expire_memory_record(memory_id, datetime.now(UTC).isoformat())
            return None
        return record if self._visible(record, retrieval) else None

    def search(
        self,
        retrieval: MemoryRetrieval | str,
        *legacy_args: object,
    ) -> tuple[MemoryRecord, ...]:
        if isinstance(retrieval, str):
            if (
                len(legacy_args) != 2
                or not isinstance(legacy_args[0], str)
                or not isinstance(legacy_args[1], str)
            ):
                raise MemoryValidationError(
                    "legacy memory.search requires workspace, scope and query"
                )
            workspace_id = retrieval
            scope = legacy_args[0]
            query = legacy_args[1]
            try:
                scope_value = MemoryScope(scope)
            except ValueError as exc:
                raise MemoryValidationError("unknown legacy memory scope") from exc
            retrieval = MemoryRetrieval(
                query,
                workspace_id,
                "legacy-api",
                session_id=(
                    scope if scope_value in {MemoryScope.WORKING, MemoryScope.SESSION} else None
                ),
                task_id=scope if scope_value == MemoryScope.TASK else None,
                scopes=(scope_value,),
                max_classification=MemoryClassification.INTERNAL,
            )
        if not isinstance(retrieval, MemoryRetrieval):
            raise MemoryValidationError("memory.search requires a MemoryRetrieval")
        retrieval.validate()
        now = datetime.now(UTC)
        self.store.expire_memories(now.isoformat())
        rows = self.store.search_memory_records(
            workspace_id=retrieval.workspace_id,
            agent_id=retrieval.agent_id,
            scopes=tuple(scope.value for scope in retrieval.scopes),
            session_id=retrieval.session_id,
            task_id=retrieval.task_id,
            max_classification=_CLASSIFICATION_RANK[retrieval.max_classification],
            include_quarantined=retrieval.include_quarantined,
        )
        query_tokens = set(re.findall(r"[a-z0-9_]{2,}", retrieval.query.lower()))
        scored: list[tuple[int, str, MemoryRecord]] = []
        for row in rows:
            record = self._row_to_record(row)
            if not self._visible(record, retrieval):
                continue
            if not self._scope_accessible(record, retrieval):
                continue
            text = f"{record.memory_key} {record.content}".lower()
            score = sum(1 for token in query_tokens if token in text)
            if retrieval.query.strip() and score == 0:
                continue
            scored.append((score, record.updated_at.isoformat(), record))
        scored.sort(key=lambda item: (-item[0], item[1], item[2].memory_id))
        telemetry().record_memory(
            operation="search",
            scope=",".join(scope.value for scope in retrieval.scopes),
        )
        return tuple(item[2] for item in scored[: retrieval.limit])

    def delete(
        self,
        memory_id: str,
        retrieval: MemoryRetrieval,
        *,
        now: datetime | None = None,
    ) -> None:
        retrieval.validate()
        record = self.get(memory_id, retrieval)
        if record is None:
            return
        self.store.delete_memory_record(memory_id, (now or datetime.now(UTC)).isoformat())
        telemetry().record_memory(operation="delete", scope=record.scope.value)

    def quarantine(
        self,
        memory_id: str,
        retrieval: MemoryRetrieval,
        reason: str,
        *,
        now: datetime | None = None,
    ) -> None:
        retrieval.validate()
        if not reason.strip():
            raise MemoryValidationError("quarantine reason is required")
        record = self.get(memory_id, retrieval)
        if record is None:
            return
        self.store.quarantine_memory_record(
            memory_id,
            reason.strip(),
            (now or datetime.now(UTC)).isoformat(),
        )
        telemetry().record_memory(operation="quarantine", scope=record.scope.value)

    def assemble_context(
        self,
        retrieval: MemoryRetrieval,
        *,
        max_items: int = 40,
    ) -> AssembledContext:
        records = self.search(retrieval)[:max_items]
        items = tuple(
            ContextItem(
                item.memory_id,
                item.content,
                item.scope,
                item.classification,
                item.trust,
                item.provenance,
                item.version,
            )
            for item in records
        )
        telemetry().record_memory(
            operation="assemble_context",
            scope=",".join(scope.value for scope in retrieval.scopes),
        )
        return AssembledContext(
            tuple(item for item in items if item.trust == MemoryTrust.TRUSTED_INSTRUCTION),
            tuple(item for item in items if item.trust == MemoryTrust.VERIFIED_FACT),
            tuple(item for item in items if item.trust == MemoryTrust.UNTRUSTED_CONTENT),
            tuple(item for item in items if item.trust == MemoryTrust.QUARANTINED),
            len(items),
        )

    @staticmethod
    def _visible(record: MemoryRecord, retrieval: MemoryRetrieval) -> bool:
        if record.state == MemoryState.QUARANTINED:
            return retrieval.include_quarantined
        if record.state != MemoryState.ACTIVE:
            return False
        if not retrieval.include_untrusted and record.trust == MemoryTrust.UNTRUSTED_CONTENT:
            return False
        return (
            _CLASSIFICATION_RANK[record.classification]
            <= _CLASSIFICATION_RANK[retrieval.max_classification]
        )

    @staticmethod
    def _scope_accessible(record: MemoryRecord, retrieval: MemoryRetrieval) -> bool:
        if record.scope not in retrieval.scopes:
            return False
        if record.scope in {MemoryScope.SESSION, MemoryScope.WORKING}:
            return record.scope_id == retrieval.session_id
        if record.scope == MemoryScope.TASK:
            return record.scope_id == retrieval.task_id
        if record.scope == MemoryScope.AGENT:
            return record.scope_id == retrieval.agent_id
        return record.scope == MemoryScope.LONG_TERM and record.scope_id == retrieval.workspace_id

    @classmethod
    def _assert_access(cls, record: MemoryRecord, retrieval: MemoryRetrieval) -> None:
        if record.workspace_id != retrieval.workspace_id:
            raise MemoryAccessError("memory belongs to another workspace")
        if record.agent_id != retrieval.agent_id:
            raise MemoryAccessError("memory belongs to another agent")
        if not cls._scope_accessible(record, retrieval):
            raise MemoryAccessError("memory scope is outside the retrieval context")

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
        provenance_data = json.loads(row["provenance"])
        provenance = MemoryProvenance(
            MemorySourceType(provenance_data["source_type"]),
            provenance_data["source_id"],
            provenance_data.get("actor_id"),
            provenance_data.get("origin"),
            datetime.fromisoformat(provenance_data["collected_at"]),
            provenance_data.get("parent_digest"),
        )
        return MemoryRecord(
            row["memory_id"],
            row["workspace_id"],
            MemoryScope(row["scope"]),
            row["scope_id"],
            row["agent_id"],
            row["memory_key"],
            row["content"],
            MemoryClassification(row["classification"]),
            MemoryTrust(row["trust"]),
            MemoryState(row["state"]),
            int(row["version"]),
            provenance,
            row["content_digest"],
            datetime.fromisoformat(row["created_at"]),
            datetime.fromisoformat(row["updated_at"]),
            datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
            row["quarantine_reason"],
        )
