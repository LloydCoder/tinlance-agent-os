"""Scoped, classified local context/memory with explicit trust boundaries."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4
from .store import StateStore
from .domain import utc_now

class DataClassification(StrEnum):
    PUBLIC="public"; INTERNAL="internal"; CONFIDENTIAL="confidential"; RESTRICTED="restricted"

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
    def put(self, workspace_id: str, scope: str, classification: DataClassification, content: str) -> MemoryItem:
        if not all(x.strip() for x in (workspace_id,scope,content)): raise ValueError("memory fields are required")
        if classification is DataClassification.RESTRICTED:
            raise PermissionError("restricted memory requires an external governed secret/memory provider")
        item=MemoryItem(str(uuid4()),workspace_id,scope,classification,content,utc_now().isoformat())
        self.store.put_memory((item.memory_id,item.workspace_id,item.scope,item.classification.value,item.content,item.created_at)); return item
    def search(self, workspace_id: str, scope: str, query: str) -> tuple[MemoryItem,...]:
        rows=self.store.execute("SELECT memory_id,workspace_id,scope,classification,content,created_at FROM memory WHERE workspace_id=? AND scope=? AND content LIKE ? ORDER BY created_at DESC",(workspace_id,scope,"%"+query+"%"))
        return tuple(MemoryItem(r[0],r[1],r[2],DataClassification(r[3]),r[4],r[5]) for r in rows)
