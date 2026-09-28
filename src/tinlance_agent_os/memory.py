"""Scoped, classified local context/memory."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4

from .domain import utc_now
from .store import StateStore


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass(frozen=True, slots=True)
class MemoryItem:
    memory_id: str
    workspace_id: str
    scope: str
    classification: DataClassification
    content: str
    created_at: str


@dataclass(slots=True)
class MemoryStore:
    store: StateStore

    def put(
        self,
        workspace_id: str,
        scope: str,
        classification: DataClassification,
        content: str,
    ) -> MemoryItem:
        if not all(value.strip() for value in (workspace_id, scope, content)):
            raise ValueError("memory fields are required")
        if classification in {DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED}:
            raise PermissionError(
                "confidential and restricted memory require an external governed memory provider"
            )
        item = MemoryItem(
            str(uuid4()),
            workspace_id,
            scope,
            classification,
            content,
            utc_now().isoformat(),
        )
        self.store.put_memory(
            (
                item.memory_id,
                item.workspace_id,
                item.scope,
                item.classification.value,
                item.content,
                item.created_at,
            )
        )
        return item

    def search(
        self,
        workspace_id: str,
        scope: str,
        query: str,
        *,
        limit: int = 100,
    ) -> tuple[MemoryItem, ...]:
        if not workspace_id.strip() or not scope.strip() or not query.strip():
            raise ValueError("workspace_id, scope and query are required")
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        rows = self.store.query(
            "SELECT memory_id,workspace_id,scope,classification,content,created_at "
            "FROM memory WHERE workspace_id=? AND scope=? AND content LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (workspace_id, scope, f"%{query}%", limit),
        )
        return tuple(
            MemoryItem(
                row[0],
                row[1],
                row[2],
                DataClassification(row[3]),
                row[4],
                row[5],
            )
            for row in rows
        )
